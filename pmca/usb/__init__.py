from collections import namedtuple

from .driver import *
from ..util import *

MscDeviceInfo = namedtuple('MscDeviceInfo', 'manufacturer, model')
MtpDeviceInfo = namedtuple('MtpDeviceInfo', 'manufacturer, model, serialNumber, operationsSupported, vendorExtension')

class MscException(Exception):
 pass

class UnknownMscException(MscException):
 pass

class MtpException(Exception):
 pass

class InvalidCommandException(Exception):
 pass


class MscDevice(object):
 """Manages communication with a USB mass storage device"""
 MSC_OC_INQUIRY = 0x12

 MSC_SENSE_InvalidCommandOperationCode = (0x5, 0x20, 0x0)

 def __init__(self, driver):
  self.driver = driver
  self.reset()

 def _checkResponse(self, sense):
  if sense != MSC_SENSE_OK:
   msg = 'Mass storage error: Sense 0x%x 0x%x 0x%x' % sense
   if sense == self.MSC_SENSE_InvalidCommandOperationCode:
    raise InvalidCommandException(msg)
   elif sense == MSC_SENSE_ERROR_UNKNOWN:
    raise UnknownMscException(msg)
   else:
    raise MscException(msg)

 def reset(self):
  self.driver.reset()
  self.driver.sendCommand(6 * b'\0')

 def _sendInquiryCommand(self, size):
  response, data = self.driver.sendReadCommand(dump8(self.MSC_OC_INQUIRY) + 3*b'\0' + dump8(size) + b'\0', size)
  self._checkResponse(response)
  return data

 def getDeviceInfo(self):
  """SCSI Inquiry command"""
  l = 5 + parse8(self._sendInquiryCommand(5)[4:5])
  data = self._sendInquiryCommand(l)

  vendor = data[8:16].decode('latin1').rstrip(' \0')
  product = data[16:32].decode('latin1').rstrip(' \0')
  return MscDeviceInfo(vendor, product)


class MtpDevice(object):
 """Manages communication with a PTP/MTP device. Inspired by libptp2"""
 PTP_OC_GetDeviceInfo = 0x1001
 PTP_OC_OpenSession = 0x1002
 PTP_OC_CloseSession = 0x1003
 PTP_RC_OK = 0x2001
 PTP_RC_SessionNotOpen = 0x2003
 PTP_RC_ParameterNotSupported = 0x2006
 PTP_RC_DeviceBusy = 0x2019
 PTP_RC_SessionAlreadyOpened = 0x201E

 def __init__(self, driver):
  self.driver = driver
  self.reset()
  self.openSession()

 def _checkResponse(self, code, acceptedCodes=[]):
  if code not in [self.PTP_RC_OK] + acceptedCodes:
   msg = 'MTP error 0x%x' % code
   if code == self.PTP_RC_ParameterNotSupported:
    raise InvalidCommandException(msg)
   else:
    raise MtpException(msg)

 def _parseString(self, data, offset):
  length = parse8(data[offset:offset+1])
  offset += 1
  end = offset + 2*length
  return end, data[offset:end].decode('utf16')[:-1]

 def _parseIntArray(self, data, offset):
  length = parse32le(data[offset:offset+4])
  offset += 4
  end = offset + 2*length
  return end, [parse16le(data[o:o+2]) for o in range(offset, end, 2)]

 def _parseDeviceInfo(self, data):
  offset = 8
  offset, vendorExtension = self._parseString(data, offset)
  offset += 2

  offset, operationsSupported = self._parseIntArray(data, offset)
  offset, eventsSupported = self._parseIntArray(data, offset)
  offset, devicePropertiesSupported = self._parseIntArray(data, offset)
  offset, captureFormats = self._parseIntArray(data, offset)
  offset, imageFormats = self._parseIntArray(data, offset)

  offset, manufacturer = self._parseString(data, offset)
  offset, model = self._parseString(data, offset)
  offset, version = self._parseString(data, offset)
  offset, serial = self._parseString(data, offset)

  return MtpDeviceInfo(manufacturer, model, serial, set(operationsSupported), vendorExtension)

 def reset(self):
  self.driver.reset()

 def openSession(self, id=1):
  """Opens a new MTP session"""
  response = self.driver.sendCommand(self.PTP_OC_OpenSession, [id])
  self._checkResponse(response, [self.PTP_RC_SessionAlreadyOpened])

 def closeSession(self):
  """Closes the current session"""
  response = self.driver.sendCommand(self.PTP_OC_CloseSession, [])
  self._checkResponse(response, [self.PTP_RC_SessionNotOpen])

 def getDeviceInfo(self):
  """Gets and parses device information"""
  response, data = self.driver.sendReadCommand(self.PTP_OC_GetDeviceInfo, [])
  self._checkResponse(response)
  return self._parseDeviceInfo(data)
