"""A wrapper to use libusb. Default on linux, on Windows you have to install a generic driver for your camera"""

import usb.core

from . import *
from ...util import *

PtpHeader = Struct('PtpHeader', [
 ('size', Struct.INT32),
 ('type', Struct.INT16),
 ('code', Struct.INT16),
 ('transaction', Struct.INT32),
])

def listDevices():
 """Lists all detected USB devices"""
 for dev in usb.core.find(find_all=True):
  interface = dev.get_active_configuration()[(0, 0)]
  yield UsbDevice(dev, dev.idVendor, dev.idProduct, interface.bInterfaceClass)


class UsbDriver:
 """Bulk reading and writing to USB devices"""
 USB_ENDPOINT_TYPE_BULK = 2
 USB_ENDPOINT_MASK = 1
 USB_ENDPOINT_OUT = 0
 USB_ENDPOINT_IN = 1

 def __init__(self, device):
  self.dev = device.handle
  self.epIn = self._findEndpoint(self.USB_ENDPOINT_TYPE_BULK, self.USB_ENDPOINT_IN)
  self.epOut = self._findEndpoint(self.USB_ENDPOINT_TYPE_BULK, self.USB_ENDPOINT_OUT)

 def _findEndpoint(self, type, direction):
  interface = self.dev.get_active_configuration()[(0, 0)]
  for ep in interface:
   if ep.bmAttributes == type and ep.bEndpointAddress & self.USB_ENDPOINT_MASK == direction:
    return ep.bEndpointAddress
  raise Exception('No endpoint found')

 def reset(self):
  if self.dev.backend.__module__ == 'usb.backend.libusb1':
   self.dev.reset()

 def read(self, length):
  return self.dev.read(self.epIn, length).tostring()

 def write(self, data):
  return self.dev.write(self.epOut, data)


class MtpDriver(UsbDriver):
 """Send and receive PTP/MTP packages to a device. Inspired by libptp2"""
 MAX_PKG_LEN = 512
 TYPE_COMMAND = 1
 TYPE_DATA = 2
 TYPE_RESPONSE = 3

 def _writePtp(self, type, code, transaction, data=''):
  self.write(PtpHeader.pack(
   size = PtpHeader.size + len(data),
   type = type,
   code = code,
   transaction = transaction,
  ) + data)

 def _readPtp(self):
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
  self._writePtp(self.TYPE_COMMAND, code, self.transaction, ''.join([dump32le(arg) for arg in args]))

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
