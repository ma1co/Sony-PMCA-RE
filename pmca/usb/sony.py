"""Methods to communicate with Sony MTP devices"""

import binascii
from collections import namedtuple
from io import BytesIO

from . import *
from ..util import *

CameraInfo = namedtuple('CameraInfo', 'plist, modelName, modelCode, serial')

ResponseMessage = namedtuple('ResponseMessage', 'data')
RequestMessage = namedtuple('RequestMessage', 'data')
InitResponseMessage = namedtuple('InitResponseMessage', 'data')
SslStartMessage = namedtuple('SslStartMessage', 'connectionId, host')
SslSendDataMessage = namedtuple('SslSendDataMessage', 'connectionId, data')
SslEndMessage = namedtuple('SslEndMessage', 'connectionId')

SONY_ID_VENDOR = 0x054c
SONY_MANUFACTURER = 'Sony Corporation'
SONY_MANUFACTURER_SHORT = 'Sony'
SONY_MSC_MODEL = 'DSC'


def isSonyMscCamera(info):
 """Pass a mass storage device info tuple. Guesses if the device is a camera in mass storage mode."""
 return info.manufacturer == SONY_MANUFACTURER_SHORT and info.model == SONY_MSC_MODEL

def isSonyMtpCamera(info):
 """Pass an MTP device info tuple. Guesses if the device is a camera in MTP mode."""
 operations = frozenset([
  SonyMtpCamera.PTP_OC_SonyDiExtCmd_write,
  SonyMtpCamera.PTP_OC_SonyDiExtCmd_read,
  SonyMtpCamera.PTP_OC_SonyReqReconnect,
 ])
 return info.manufacturer == SONY_MANUFACTURER and info.vendorExtension == '' and operations <= info.operationsSupported

def isSonyMtpAppInstaller(info):
 """Pass an MTP device info tuple. Guesses if the device is a camera in app installation mode."""
 operations = frozenset([
  SonyMtpAppInstaller.PTP_OC_GetProxyMessageInfo,
  SonyMtpAppInstaller.PTP_OC_GetProxyMessage,
  SonyMtpAppInstaller.PTP_OC_SendProxyMessageInfo,
  SonyMtpAppInstaller.PTP_OC_SendProxyMessage,
 ])
 return info.manufacturer == SONY_MANUFACTURER and 'sony.net/SEN_PRXY_MSG:' in info.vendorExtension and operations <= info.operationsSupported


class SonyMscCamera(MscDevice):
 """Methods to communicate a camera in mass storage mode"""
 MSC_OC_ExtCmd = 0x7a

 def sendSonyExtCommand(self, cmd, data, bufferSize):
  command = dump8(self.MSC_OC_ExtCmd) + dump32le(cmd) + 7*'\x00'
  response = self.driver.sendWriteCommand(command, data)
  self._checkResponse(response)
  response, data = self.driver.sendReadCommand(command, bufferSize)
  self._checkResponse(response)
  return data


class SonyMtpCamera(MtpDevice):
 """Methods to communicate a camera in MTP mode"""

 # Operation codes (defined in libInfraMtpServer.so)
 PTP_OC_SonyDiExtCmd_write = 0x9280
 PTP_OC_SonyDiExtCmd_read = 0x9281
 PTP_OC_SonyReqReconnect = 0x9282
 PTP_OC_SonyGetBurstshotGroupNum = 0x9283
 PTP_OC_SonyGetBurstshotObjectHandles = 0x9284
 PTP_OC_SonyGetAVIndexID = 0x9285

 def sendSonyExtCommand(self, cmd, data, bufferSize):
  response = self.PTP_RC_DeviceBusy
  while response == self.PTP_RC_DeviceBusy:
   response = self.driver.sendWriteCommand(self.PTP_OC_SonyDiExtCmd_write, [cmd], data)
  self._checkResponse(response)

  response = self.PTP_RC_DeviceBusy
  while response == self.PTP_RC_DeviceBusy:
   response, data = self.driver.sendReadCommand(self.PTP_OC_SonyDiExtCmd_read, [cmd])
  self._checkResponse(response)
  return data

 def switchToMsc(self):
  """Tells the camera to switch to mass storage mode"""
  response = self.driver.sendCommand(self.PTP_OC_SonyReqReconnect, [0])
  self._checkResponse(response)


class SonyExtCmdCamera:
 """Methods to send Sony external commands to a camera"""

 # DevInfoSender (libInfraDevInfoSender.so)
 SONY_CMD_DevInfoSender_GetModelInfo = (1, 1)
 SONY_CMD_DevInfoSender_GetSupportedCommandIds = (1, 2)

 # KikiLogSender (libInfraKikiLogSender.so)
 SONY_CMD_KikiLogSender_InitKikiLog = (2, 1)
 SONY_CMD_KikiLogSender_ReadKikiLog = (2, 2)

 # ExtBackupCommunicator (libInfraExtBackupCommunicator.so)
 SONY_CMD_ExtBackupCommunicator_GetSupportedCommandIds = (4, 1)
 SONY_CMD_ExtBackupCommunicator_NotifyBackupType = (4, 2)
 SONY_CMD_ExtBackupCommunicator_NotifyBackupStart = (4, 3)
 SONY_CMD_ExtBackupCommunicator_NotifyBackupFinish = (4, 4)
 SONY_CMD_ExtBackupCommunicator_ForcePowerOff = (4, 5)
 SONY_CMD_ExtBackupCommunicator_GetRegisterableHostNum = (4, 6)
 SONY_CMD_ExtBackupCommunicator_GetRegisteredHostNetInfo = (4, 7)
 SONY_CMD_ExtBackupCommunicator_ForceRegistHostNetInfo = (4, 8)
 SONY_CMD_ExtBackupCommunicator_GetDeviceNetInfo = (4, 9)

 # ScalarExtCmdPlugIn (libInfraScalarExtCmdPlugIn.so)
 SONY_CMD_ScalarExtCmdPlugIn_GetSupportedCommandIds = (5, 1)
 SONY_CMD_ScalarExtCmdPlugIn_NotifyScalarDlmode = (5, 2)

 # LensCommunicator (libInfraLensCommunicator.so)
 SONY_CMD_LensCommunicator_GetSupportedCommandIds = (6, 1)
 SONY_CMD_LensCommunicator_GetMountedLensInfo = (6, 2)

 BUFFER_SIZE = 8192

 def __init__(self, dev):
  self.dev = dev

 def _sendCommand(self, cmd):
  data = self.dev.sendSonyExtCommand(cmd[0], 4*'\x00' + dump32le(cmd[1]) + 8*'\x00', self.BUFFER_SIZE)
  size = parse32le(data[:4])
  return data[16:16+size]

 def getCameraInfo(self):
  """Gets information about the camera"""
  data = BytesIO(self._sendCommand(self.SONY_CMD_DevInfoSender_GetModelInfo))
  plistSize = parse32le(data.read(4))
  plistData = data.read(plistSize)
  data.read(4)
  modelSize = parse8(data.read(1))
  modelName = data.read(modelSize)
  modelCode = binascii.hexlify(data.read(5))
  serial = binascii.hexlify(data.read(4))
  return CameraInfo(plistData, modelName, modelCode, serial)

 def getKikiLog(self):
  """Reads the first part of /tmp/kikilog.dat"""
  self._sendCommand(self.SONY_CMD_KikiLogSender_InitKikiLog)
  kikilog = ''
  remaining = 1
  while remaining:
   data = BytesIO(self._sendCommand(self.SONY_CMD_KikiLogSender_ReadKikiLog))
   data.read(4)
   remaining = parse32le(data.read(4))
   size = parse32le(data.read(4))
   kikilog += data.read(size)
  return kikilog[24:]

 def switchToAppInstaller(self):
  """Tells the camera to switch to app installation mode"""
  self._sendCommand(self.SONY_CMD_ScalarExtCmdPlugIn_NotifyScalarDlmode)

 def powerOff(self):
  """Forces the camera to turn off"""
  self._sendCommand(self.SONY_CMD_ExtBackupCommunicator_ForcePowerOff)


class SonyUpdaterCamera:
 """Methods to send updater commands to a camera"""

 # from libupdaterufp.so
 SONY_CMD_Updater = 0
 SONY_CMD_Updater_init = 0x1
 SONY_CMD_Updater_chk_guard = 0x10
 SONY_CMD_Updater_query_version = 0x20
 SONY_CMD_Updater_switch_mode = 0x30
 SONY_CMD_Updater_write_firm = 0x40
 SONY_CMD_Updater_complete = 0x100
 SONY_CMD_Updater_get_state = 0x200

 DIRECTION_OUT = 0
 DIRECTION_IN = 1

 BUFFER_SIZE = 512

 def __init__(self, dev):
  self.dev = dev

 def _sendCommand(self, command, direction, data='', sequence=0):
  header = dump32le(len(data)) + '\x00\x01' + dump16le(command) + dump8(direction) + '\x00' + dump16le(sequence) + 20*'\x00'
  return self.dev.sendSonyExtCommand(self.SONY_CMD_Updater, header + data, self.BUFFER_SIZE)

 def getFirmwareVersion(self):
  """Returns the camera's firmware version"""
  data = self._sendCommand(self.SONY_CMD_Updater_query_version, self.DIRECTION_IN)
  return '%x.%02x' % (parse8(data[34]), parse8(data[32]))


class SonyMtpAppInstaller(MtpDevice):
 """Methods to communicate a camera in app installation mode"""

 # Operation codes (defined in libUsbAppDlSvr.so)
 PTP_OC_GetProxyMessageInfo = 0x9488
 PTP_OC_GetProxyMessage = 0x9489
 PTP_OC_SendProxyMessageInfo = 0x948c
 PTP_OC_SendProxyMessage = 0x948d
 PTP_OC_GetDeviceCapability = 0x940a

 def _write(self, data):
  info = 4*'\x00' + '\x81\xb4\x00\x00' + dump32le(len(data)) + 40*'\x00' + '\x02\x41\x00\x00' + 4*'\x00'
  response = self.driver.sendWriteCommand(self.PTP_OC_SendProxyMessageInfo, [], info)
  self._checkResponse(response)
  response = self.driver.sendWriteCommand(self.PTP_OC_SendProxyMessage, [], data)
  self._checkResponse(response)

 def _read(self):
  response, data = self.driver.sendReadCommand(self.PTP_OC_GetProxyMessageInfo, [0])
  self._checkResponse(response)
  response, data = self.driver.sendReadCommand(self.PTP_OC_GetProxyMessage, [0])
  self._checkResponse(response, [0xa488])
  return data

 def receive(self):
  """Receives and parses the next message from the camera"""
  data = self._read()
  if data == '':
   return None
  else:
   type = data[:4]
   if type == '\x00\x02\x00\x01':
    return ResponseMessage(data[6:-1])
   elif type == '\x00\x02\x00\x00':
    return RequestMessage(data[6:-1])
   elif type == '\x00\x00\x00\x01' or type == '\x00\x01\x00\x01':
    type = data[6:8]
    if type == '\x04\x01':
     return InitResponseMessage(data[20:])
    elif type == '\x05\x01':
     return SslStartMessage(parse16be(data[20:22]), data[28:])
    elif type == '\x05\x02':
     return SslEndMessage(parse16be(data[20:22]))
    elif type == '\x05\x03':
     return SslSendDataMessage(parse16be(data[20:22]), data[26:])
    else:
     raise Exception('Unknown type 2: %s' % repr(type))
   else:
    raise Exception('Unknown type 1: %s' % repr(type))

 def _receiveResponse(self, type):
  msg = None
  while msg == None:
   msg = self.receive()
  if not isinstance(msg, type):
   raise Exception('Wrong response: %s' % str(msg))
  return msg

 def _sendCommand(self, type1, type2, data):
  self._write(type1 + '\x00\x00' + type2 + dump32be(len(data) + 18) + 8*'\x00' + data)

 def emptyBuffer(self):
  """Receives and discards all pending messages from the camera"""
  msg = True
  while msg:
   msg = self.receive()

 def sendInit(self):
  """Send an initialization message to the camera"""
  data = '\x00\x02TCPT\x00\x01REST\x01\x00'
  self._sendCommand('\x00\x00\x00\x01', '\x04\x00', data)
  self._receiveResponse(InitResponseMessage)

 def sendRequest(self, data):
  """Sends a REST request to the camera. Used to start communication"""
  self._write('\x00\x02\x00\x01' + dump16be(len(data)) + data)
  return self._receiveResponse(ResponseMessage).data

 def sendSslData(self, req, data):
  """Sends raw SSL response data to the camera"""
  self._sendCommand('\x00\x01\x00\x01', '\x05\x03', dump16be(req) + dump32be(len(data)) + data)

 def sendSslEnd(self, req):
  """Lets the camera know that the SSL socket has been closed"""
  self._sendCommand('\x00\x01\x00\x01', '\x05\x04', dump16be(req) + '\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00')

 def sendEnd(self):
  """Ends the communication with the camera"""
  self._sendCommand('\x00\x00\x00\x01', '\x04\x02', 8*'\x00')
