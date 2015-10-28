from collections import namedtuple

from ..util import *

DeviceInfo = namedtuple('DeviceInfo', 'manufacturer, model, serialNumber, operationsSupported, vendorExtension')

class MtpDevice:
 """Manages communication with a PTP/MTP device. Inspired by libptp2"""
 PTP_OC_GetDeviceInfo = 0x1001
 PTP_OC_OpenSession = 0x1002
 PTP_OC_CloseSession = 0x1003
 PTP_RC_OK = 0x2001
 PTP_RC_SessionNotOpen = 0x2003
 PTP_RC_SessionAlreadyOpened = 0x201E

 def __init__(self, driver):
  self.driver = driver
  self.openSession()

 def _checkResponse(self, code, acceptedCodes=[]):
  if code not in [self.PTP_RC_OK] + acceptedCodes:
   raise Exception('Response code not OK: 0x%x' % code)

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

  return DeviceInfo(manufacturer, model, serial, set(operationsSupported), vendorExtension)

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
