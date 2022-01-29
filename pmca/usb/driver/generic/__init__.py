import abc
from .. import *
from ....util import *

class GenericUsbException(Exception):
 pass

PtpHeader = Struct('PtpHeader', [
 ('size', Struct.INT32),
 ('type', Struct.INT16),
 ('code', Struct.INT16),
 ('transaction', Struct.INT32),
])

MscCommandBlockWrapper = Struct('MscCommandBlockWrapper', [
 ('signature', Struct.STR % 4),
 ('tag', Struct.INT32),
 ('dataTransferLength', Struct.INT32),
 ('flags', Struct.INT8),
 ('lun', Struct.INT8),
 ('commandLength', Struct.INT8),
 ('command', Struct.STR % 16),
])

MscCommandStatusWrapper = Struct('MscCommandStatusWrapper', [
 ('signature', Struct.STR % 4),
 ('tag', Struct.INT32),
 ('dataResidue', Struct.INT32),
 ('status', Struct.INT8),
])


class BaseUsbBackend(abc.ABC):
 @abc.abstractmethod
 def reset(self):
  pass

 @abc.abstractmethod
 def clearHalt(self, ep):
  pass

 @abc.abstractmethod
 def getId(self):
  pass

 @abc.abstractmethod
 def getEndpoints(self):
  pass

 @abc.abstractmethod
 def read(self, ep, length, timeout=None):
  pass

 @abc.abstractmethod
 def write(self, ep, data):
  pass

 @abc.abstractmethod
 def classInterfaceRequestOut(self, request, value, index, data=b''):
  pass

 @abc.abstractmethod
 def vendorRequestOut(self, request, value, index, data=b''):
  pass


class GenericUsbDriver(BaseUsbDriver):
 USB_ENDPOINT_TYPE_BULK = 2
 USB_ENDPOINT_MASK = 0x80
 USB_ENDPOINT_OUT = 0
 USB_ENDPOINT_IN = 0x80

 def __init__(self, backend):
  self.backend = backend
  self.epIn = list(self._findEndpoints(self.USB_ENDPOINT_TYPE_BULK, self.USB_ENDPOINT_IN))
  if not self.epIn:
   raise Exception('No in endpoint found')
  self.epOut = list(self._findEndpoints(self.USB_ENDPOINT_TYPE_BULK, self.USB_ENDPOINT_OUT))
  if not self.epOut:
   raise Exception('No out endpoint found')

 def _findEndpoints(self, type, direction):
  for ep in self.backend.getEndpoints():
   if ep.bmAttributes == type and ep.bEndpointAddress & self.USB_ENDPOINT_MASK == direction:
    yield ep.bEndpointAddress

 def reset(self):
  self.backend.reset()

 def getId(self):
  return self.backend.getId()

 def read(self, length, ep=0, timeout=None):
  return self.backend.read(self.epIn[ep], length, timeout)

 def write(self, data, ep=0):
  self.backend.write(self.epOut[ep], data)

 def vendorRequestOut(self, request, value, index, data=b''):
  self.backend.vendorRequestOut(request, value, index, data)


class MscBbbDriver(GenericUsbDriver, BaseMscDriver):
 """Communicate with a USB mass storage device"""
 MSC_OC_REQUEST_SENSE = 0x03

 DIRECTION_WRITE = 0
 DIRECTION_READ = 0x80

 def _writeCommand(self, direction, command, dataSize, tag=0, lun=0):
  self.write(MscCommandBlockWrapper.pack(
   signature = b'USBC',
   tag = tag,
   dataTransferLength = dataSize,
   flags = direction,
   lun = lun,
   commandLength = len(command),
   command = command,
  ))

 def _readResponse(self, failOnError=False):
  response = MscCommandStatusWrapper.unpack(self.read(MscCommandStatusWrapper.size))
  if response.signature != b'USBS':
   raise Exception('Wrong status signature')
  if response.status != 0:
   if failOnError:
    raise Exception('Mass storage error')
   else:
    return self.requestSense()
  return MSC_SENSE_OK

 def requestSense(self):
  size = 18
  response, data = self.sendReadCommand(dump8(self.MSC_OC_REQUEST_SENSE) + 3*b'\0' + dump8(size) + b'\0', size, failOnError=True)
  return parseMscSense(data)

 def sendCommand(self, command, failOnError=False):
  self._writeCommand(self.DIRECTION_WRITE, command, 0)
  return self._readResponse(failOnError)

 def sendWriteCommand(self, command, data, failOnError=False):
  self._writeCommand(self.DIRECTION_WRITE, command, len(data))

  stalled = False
  try:
   self.write(data)
  except GenericUsbException:
   # Write stall
   stalled = True
   self.backend.clearHalt(self.epOut[0])

  sense = self._readResponse(failOnError)
  if stalled and sense == MSC_SENSE_OK:
   raise Exception('Mass storage write error')
  return sense

 def sendReadCommand(self, command, size, failOnError=False):
  self._writeCommand(self.DIRECTION_READ, command, size)

  stalled = False
  data = None
  try:
   data = self.read(size)
  except GenericUsbException:
   # Read stall
   stalled = True
   self.backend.clearHalt(self.epIn[0])

  sense = self._readResponse(failOnError)
  if stalled and sense == MSC_SENSE_OK:
   raise Exception('Mass storage read error')
  return sense, data


class MscCbiDriver(GenericUsbDriver, BaseMscDriver):
 def _writeCommand(self, command):
  self.backend.classInterfaceRequestOut(0, 0, 0, command)

 def sendCommand(self, command):
  self._writeCommand(command)
  return MSC_SENSE_OK

 def sendWriteCommand(self, command, data):
  self._writeCommand(command)
  self.write(data)
  return MSC_SENSE_OK

 def sendReadCommand(self, command, size):
  self._writeCommand(command)
  data = self.read(size)
  return MSC_SENSE_OK, data


class MtpDriver(GenericUsbDriver, BaseMtpDriver):
 """Send and receive PTP/MTP packages to a device. Inspired by libptp2"""
 MAX_PKG_LEN = 512
 TYPE_COMMAND = 1
 TYPE_DATA = 2
 TYPE_RESPONSE = 3

 def _writePtp(self, type, code, transaction, data=b''):
  self.write(PtpHeader.pack(
   size = PtpHeader.size + len(data),
   type = type,
   code = code,
   transaction = transaction,
  ) + data)

 def _readPtp(self):
  data = b''
  while data == b'':
   data = self.read(self.MAX_PKG_LEN)
  header = PtpHeader.unpack(data)
  if header.size > self.MAX_PKG_LEN:
   data += self.read(header.size - self.MAX_PKG_LEN)
  return header.type, header.code, header.transaction, data[PtpHeader.size:PtpHeader.size+header.size]

 def _readData(self):
  type, code, transaction, data = self._readPtp()
  if type != self.TYPE_DATA:
   raise Exception('Wrong response type: 0x%x' % type)
  return data

 def _readResponse(self):
  type, code, transaction, data = self._readPtp()
  if type != self.TYPE_RESPONSE:
   raise Exception('Wrong response type: 0x%x' % type)
  return code

 def _writeInitialCommand(self, code, args):
  try:
   self.transaction += 1
  except AttributeError:
   self.transaction = 0
  self._writePtp(self.TYPE_COMMAND, code, self.transaction, b''.join([dump32le(arg) for arg in args]))

 def sendCommand(self, code, args):
  """Send a PTP/MTP command without data phase"""
  self._writeInitialCommand(code, args)
  return self._readResponse()

 def sendWriteCommand(self, code, args, data):
  """Send a PTP/MTP command with write data phase"""
  self._writeInitialCommand(code, args)
  self._writePtp(self.TYPE_DATA, code, self.transaction, data)
  return self._readResponse()

 def sendReadCommand(self, code, args):
  """Send a PTP/MTP command with read data phase"""
  self._writeInitialCommand(code, args)
  data = self._readData()
  return self._readResponse(), data
