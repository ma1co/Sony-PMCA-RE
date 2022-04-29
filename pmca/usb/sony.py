"""Methods to communicate with Sony MTP devices"""

import abc
import binascii
from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta
from io import BytesIO

try:
 from Cryptodome.Hash import SHA256
except ImportError:
 from Crypto.Hash import SHA256

from . import *
from . import constants, crypto
from ..util import *
from .driver.generic import GenericUsbException

CameraInfo = namedtuple('CameraInfo', 'plist, modelName, modelCode, serial')
LensInfo = namedtuple('LensInfo', 'type, model, region, version')

ResponseMessage = namedtuple('ResponseMessage', 'data')
RequestMessage = namedtuple('RequestMessage', 'data')
InitResponseMessage = namedtuple('InitResponseMessage', 'protocols')
SslStartMessage = namedtuple('SslStartMessage', 'connectionId, host, port')
SslSendDataMessage = namedtuple('SslSendDataMessage', 'connectionId, data')
SslEndMessage = namedtuple('SslEndMessage', 'connectionId')

SONY_ID_VENDOR = 0x054c
SONY_ID_PRODUCT_UPDATER = [0x033a, 0x03e2]
SONY_ID_PRODUCT_SENSER = [0x02a9, 0x0336]
SONY_MANUFACTURER = 'Sony Corporation'
SONY_MANUFACTURER_SHORT = 'Sony'
SONY_MSC_MODELS = ['DSC', 'Camcorder']


def isSonyMscCamera(info):
 """Pass a mass storage device info tuple. Guesses if the device is a camera in mass storage mode."""
 return info.manufacturer == SONY_MANUFACTURER_SHORT and info.model in SONY_MSC_MODELS

def isSonyMscUpdaterCamera(dev):
 return dev.idVendor == SONY_ID_VENDOR and dev.idProduct in SONY_ID_PRODUCT_UPDATER

def isSonySenserCamera(dev):
 return dev.idVendor == SONY_ID_VENDOR and dev.idProduct in SONY_ID_PRODUCT_SENSER

def isSonyMtpCamera(info):
 """Pass an MTP device info tuple. Guesses if the device is a camera in MTP mode."""
 operations = frozenset([
  SonyMtpExtCmdDevice.PTP_OC_SonyDiExtCmd_write,
  SonyMtpExtCmdDevice.PTP_OC_SonyDiExtCmd_read,
  SonyMtpExtCmdDevice.PTP_OC_SonyReqReconnect,
 ])
 return info.manufacturer == SONY_MANUFACTURER and info.vendorExtension == '' and operations <= info.operationsSupported

def isSonyMtpAppInstallCamera(info):
 """Pass an MTP device info tuple. Guesses if the device is a camera in app installation mode."""
 operations = frozenset([
  SonyMtpAppInstallDevice.PTP_OC_GetProxyMessageInfo,
  SonyMtpAppInstallDevice.PTP_OC_GetProxyMessage,
  SonyMtpAppInstallDevice.PTP_OC_SendProxyMessageInfo,
  SonyMtpAppInstallDevice.PTP_OC_SendProxyMessage,
 ])
 return info.manufacturer == SONY_MANUFACTURER and 'sony.net/SEN_PRXY_MSG:' in info.vendorExtension and operations <= info.operationsSupported


class SonyUsbDevice(UsbDevice):
 pass


class SonyExtCmdDevice(SonyUsbDevice, abc.ABC):
 @abc.abstractmethod
 def sendSonyExtCommand(self, cmd, data, bufferSize):
  pass


class SonyUpdaterDevice(SonyUsbDevice, abc.ABC):
 @abc.abstractmethod
 def sendSonyExtCommand(self, cmd, data, bufferSize):
  pass


class _BaseSonyMscExtCmdDevice(MscDevice):
 """Methods to communicate a camera in mass storage mode"""
 MSC_OC_ExtCmd = 0x7a

 MSC_SENSE_DeviceBusy = (0x9, 0x81, 0x81)

 def sendSonyExtCommand(self, cmd, data, bufferSize):
  command = dump8(self.MSC_OC_ExtCmd) + dump32le(cmd) + 7*b'\0'

  response = self.MSC_SENSE_DeviceBusy
  while response == self.MSC_SENSE_DeviceBusy:
   response = self.driver.sendWriteCommand(command, data)
  self._checkResponse(response)

  if bufferSize == 0:
   return b''

  response = self.MSC_SENSE_DeviceBusy
  while response == self.MSC_SENSE_DeviceBusy:
   response, data = self.driver.sendReadCommand(command, bufferSize)
  self._checkResponse(response)
  return data


class SonyMscExtCmdDevice(_BaseSonyMscExtCmdDevice, SonyExtCmdDevice):
 pass


class SonyMscUpdaterDevice(_BaseSonyMscExtCmdDevice, SonyUpdaterDevice):
 pass


class SonyMtpExtCmdDevice(MtpDevice, SonyExtCmdDevice):
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

  if bufferSize == 0:
   return b''

  response = self.PTP_RC_DeviceBusy
  while response == self.PTP_RC_DeviceBusy:
   response, data = self.driver.sendReadCommand(self.PTP_OC_SonyDiExtCmd_read, [cmd])
  self._checkResponse(response)
  return data

 def switchToMsc(self):
  """Tells the camera to switch to mass storage mode"""
  response = self.driver.sendCommand(self.PTP_OC_SonyReqReconnect, [0])
  self._checkResponse(response)


class SonyExtCmdCamera(object):
 """Methods to send Sony external commands to a camera"""

 # DevInfoSender (libInfraDevInfoSender.so)
 SONY_CMD_DevInfoSender_GetModelInfo = (1, 1)
 SONY_CMD_DevInfoSender_GetSupportedCommandIds = (1, 2)

 # KikiLogSender (libInfraKikiLogSender.so)
 SONY_CMD_KikiLogSender_InitKikiLog = (2, 1)
 SONY_CMD_KikiLogSender_ReadKikiLog = (2, 2)

 # GpsAssist
 SONY_CMD_GpsAssist_InitGps = (3, 1)
 SONY_CMD_GpsAssist_WriteGps = (3, 2)

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

 # NetworkServiceInfo (libInfraNetworkServiceInfo.so)
 SONY_CMD_NetworkServiceInfo_GetSupportedCommandIds = (7, 1)
 SONY_CMD_NetworkServiceInfo_SetLiveStreamingServiceInfo = (7, 2)
 SONY_CMD_NetworkServiceInfo_GetLiveStreamingServiceInfo = (7, 3)
 SONY_CMD_NetworkServiceInfo_SetLiveStreamingSNSInfo = (7, 4)
 SONY_CMD_NetworkServiceInfo_GetLiveStreamingSNSInfo = (7, 5)
 SONY_CMD_NetworkServiceInfo_SetWifiAPInfo = (7, 6)
 SONY_CMD_NetworkServiceInfo_GetWifiAPInfo = (7, 7)
 SONY_CMD_NetworkServiceInfo_GetLiveStreamingLastError = (7, 8)
 SONY_CMD_NetworkServiceInfo_SetMultiWifiAPInfo = (7, 9)
 SONY_CMD_NetworkServiceInfo_GetMultiWifiAPInfo = (7, 10)

 ExtCmdHeader = Struct('ExtCmdHeader', [
  ('dataSize', Struct.INT32),
  ('cmd', Struct.INT16),
  ('direction', Struct.INT16),
  ('', 8),
 ])

 InitGpsRequest = Struct('InitGpsRequest', [
  ('firstDate', Struct.INT32),
  ('lastDate', Struct.INT32),
  ('one', Struct.INT32),
  ('crc32', Struct.INT32),
  ('size', Struct.INT32),
 ])

 InitGpsResponse = Struct('InitGpsResponse', [
  ('status', Struct.INT16),
  ('firstDate', Struct.INT32),
  ('lastDate', Struct.INT32),
 ])

 DataTransferHeader = Struct('DataTransferHeader', [
  ('sequence', Struct.INT32),
  ('remaining', Struct.INT32),
  ('dataSize', Struct.INT32),
 ])

 MountedLensInfo = Struct('MountedLensInfo', [
  ('type', Struct.INT32),
  ('versionMinor', Struct.INT8),
  ('versionMajor', Struct.INT8),
  ('model', Struct.STR % 4),
  ('region', Struct.STR % 4),
 ])

 LiveStreamingServiceInfo1 = Struct('LiveStreamingServiceInfo1', [
  ('service', Struct.INT32),
  ('enabled', Struct.INT8),
  ('macId', Struct.STR % 41),
  ('macSecret', Struct.STR % 41),
  ('macIssueTime', Struct.STR % 8),
  ('unknown', Struct.INT32),
 ])

 LiveStreamingServiceInfo2 = Struct('LiveStreamingServiceInfo2', [
  ('shortURL', Struct.STR % 101),
  ('videoFormat', Struct.INT32),
 ])

 LiveStreamingServiceInfo3 = Struct('LiveStreamingServiceInfo3', [
  ('enableRecordMode', Struct.INT8),
  ('videoTitle', Struct.STR % 401),
  ('videoDescription', Struct.STR % 401),
  ('videoTag', Struct.STR % 401),
 ])

 LiveStreamingSNSInfo = Struct('LiveStreamingSNSInfo', [
  ('twitterEnabled', Struct.INT8),
  ('twitterConsumerKey', Struct.STR % 1025),
  ('twitterConsumerSecret', Struct.STR % 1025),
  ('twitterAccessToken1', Struct.STR % 1025),
  ('twitterAccessTokenSecret', Struct.STR % 1025),
  ('twitterMessage', Struct.STR % 401),
  ('facebookEnabled', Struct.INT8),
  ('facebookAccessToken', Struct.STR % 1025),
  ('facebookMessage', Struct.STR % 401),
 ])

 APInfo = Struct('APInfo', [
  ('keyType', Struct.INT8),
  ('sid', Struct.STR % 33),
  ('', 1),
  ('key', Struct.STR % 65),
 ])

 def __init__(self, dev):
  self.dev = dev

 def _sendCommand(self, cmd, data=b'', writeBufferSize=0x2000, readBufferSize=0x2000):
  data = self.dev.sendSonyExtCommand(cmd[0], (self.ExtCmdHeader.pack(
   dataSize = len(data),
   cmd = cmd[1],
   direction = 0,
  ) + data).ljust(writeBufferSize, b'\0'), readBufferSize)
  if readBufferSize == 0:
   return b''
  return data[self.ExtCmdHeader.size:self.ExtCmdHeader.size+self.ExtCmdHeader.unpack(data).dataSize]

 def getCameraInfo(self):
  """Gets information about the camera"""
  data = BytesIO(self._sendCommand(self.SONY_CMD_DevInfoSender_GetModelInfo))
  plistSize = parse32le(data.read(4))
  plistData = data.read(plistSize)
  data.read(4)
  modelSize = parse8(data.read(1))
  modelName = data.read(modelSize).decode('latin1')
  modelCode = binascii.hexlify(data.read(5)).decode('latin1')
  serial = binascii.hexlify(data.read(4)).decode('latin1')
  return CameraInfo(plistData, modelName, modelCode, serial)

 def getUsageLog(self):
  """Reads the usage log"""
  self._sendCommand(self.SONY_CMD_KikiLogSender_InitKikiLog)
  kikilog = b''
  while True:
   data = self._sendCommand(self.SONY_CMD_KikiLogSender_ReadKikiLog)
   header = self.DataTransferHeader.unpack(data)
   kikilog += data[self.DataTransferHeader.size:self.DataTransferHeader.size+header.dataSize]
   if header.remaining == 0:
    break
  return kikilog

 def _convertGpsTimestamp(self, ts):
  return datetime(1980, 1, 6) + timedelta(hours = ts & 0xffffff)

 def getGpsData(self):
  """Returns the start and end date of the APGS data"""
  data = self._sendCommand(self.SONY_CMD_GpsAssist_InitGps, self.InitGpsRequest.pack(
   firstDate = 0,
   lastDate = 0,
   one = 1,
   crc32 = 0,
   size = 0x43800,# 30 days * 4 dates/day * 32 frames/date * (4 bytes header + 64 bytes data + 4 bytes xor checksum)/frame
  ), 0x10000, 0x200)
  info = self.InitGpsResponse.unpack(data)
  return self._convertGpsTimestamp(info.firstDate), self._convertGpsTimestamp(info.lastDate) + timedelta(hours=6)

 def writeGpsData(self, file):
  """Writes an assistme.dat file to the camera"""
  sequence = 0
  remaining = 0x43800
  while remaining > 0:
   sequence += 1
   data = file.read(0x10000 - self.ExtCmdHeader.size - self.DataTransferHeader.size)
   remaining -= len(data)
   response = self._sendCommand(self.SONY_CMD_GpsAssist_WriteGps, self.DataTransferHeader.pack(
    sequence = sequence,
    remaining = remaining,
    dataSize = len(data),
   ) + data, 0x10000, 0x200)
   if (remaining == 0 and response != b'\x01\0') or (remaining > 0 and response != b'\0\0'):
    raise Exception('Invalid response: %s' % response)

 def switchToAppInstaller(self):
  """Tells the camera to switch to app installation mode"""
  self._sendCommand(self.SONY_CMD_ScalarExtCmdPlugIn_NotifyScalarDlmode, readBufferSize=0)

 def powerOff(self):
  """Forces the camera to turn off"""
  self._sendCommand(self.SONY_CMD_ExtBackupCommunicator_ForcePowerOff, readBufferSize=0)

 def getMacAddress(self):
  """Returns the camera's MAC address"""
  addr = self._sendCommand(self.SONY_CMD_ExtBackupCommunicator_GetDeviceNetInfo)[2:8]
  return ':'.join('%02X' % parse8(addr[i:i+1]) for i in range(len(addr)))

 def getLensInfo(self):
  """Returns information about the mounted lens"""
  info = self.MountedLensInfo.unpack(self._sendCommand(self.SONY_CMD_LensCommunicator_GetMountedLensInfo))
  return LensInfo(
   type = info.type,
   model = parse32be(info.model[0:2] + info.model[3:4] + info.model[2:3]),
   region = parse32be(info.region),
   version = '%x.%02x' % (info.versionMajor, info.versionMinor),
  )

 def getLiveStreamingServiceInfo(self):
  """Returns the live streaming ustream configuration"""
  data = BytesIO(self._sendCommand(self.SONY_CMD_NetworkServiceInfo_GetLiveStreamingServiceInfo))
  data.read(4)
  for i in range(parse32le(data.read(4))):
   info1 = self.LiveStreamingServiceInfo1.unpack(data.read(self.LiveStreamingServiceInfo1.size))
   channels = [parse32le(data.read(4)) for j in range(parse32le(data.read(4)))]
   info2 = self.LiveStreamingServiceInfo2.unpack(data.read(self.LiveStreamingServiceInfo2.size))
   supportedFormats = [parse32le(data.read(4)) for j in range(parse32le(data.read(4)))]
   info3 = self.LiveStreamingServiceInfo3.unpack(data.read(self.LiveStreamingServiceInfo3.size))
   yield OrderedDict(e for d in [
    info1._asdict(),
    {'channels': channels},
    info2._asdict(),
    {'supportedFormats': supportedFormats},
    info3._asdict(),
   ] for e in d.items())

 def setLiveStreamingServiceInfo(self, data):
  """Sets the live streaming ustream configuration"""
  return self._sendCommand(self.SONY_CMD_NetworkServiceInfo_SetLiveStreamingServiceInfo, data)

 def getLiveStreamingSocialInfo(self):
  """Returns the live streaming social media configuration"""
  return self.LiveStreamingSNSInfo.unpack(self._sendCommand(self.SONY_CMD_NetworkServiceInfo_GetLiveStreamingSNSInfo))

 def setLiveStreamingSocialInfo(self, data):
  """Sets the live streaming social media configuration"""
  return self._sendCommand(self.SONY_CMD_NetworkServiceInfo_SetLiveStreamingSNSInfo, data)

 def _parseAPs(self, data):
  for i in range(parse32le(data.read(4))):
   yield self.APInfo.unpack(data.read(self.APInfo.size))

 def getWifiAPInfo(self):
  """Returns the live streaming access point configuration"""
  for ap in self._parseAPs(BytesIO(self._sendCommand(self.SONY_CMD_NetworkServiceInfo_GetWifiAPInfo))):
   yield ap

 def setWifiAPInfo(self, data):
  """Sets the live streaming access point configuration"""
  return self._sendCommand(self.SONY_CMD_NetworkServiceInfo_SetWifiAPInfo, data)

 def getMultiWifiAPInfo(self):
  """Returns the live streaming multi access point configuration"""
  for ap in self._parseAPs(BytesIO(self._sendCommand(self.SONY_CMD_NetworkServiceInfo_GetMultiWifiAPInfo))):
   yield ap

 def setMultiWifiAPInfo(self, data):
  """Sets the live streaming multi access point configuration"""
  return self._sendCommand(self.SONY_CMD_NetworkServiceInfo_SetMultiWifiAPInfo, data)


class SonyUpdaterSequenceError(Exception):
 def __init__(self):
  Exception.__init__(self, 'Wrong updater command sequence')


class SonyUpdaterCamera(object):
 """Methods to send updater commands to a camera"""

 # from libupdaterufp.so
 SONY_CMD_Updater = 0
 CMD_INIT = 0x1
 CMD_CHK_GUARD = 0x10
 CMD_QUERY_VERSION = 0x20
 CMD_SWITCH_MODE = 0x30
 CMD_WRITE_FIRM = 0x40
 CMD_COMPLETE = 0x100
 CMD_GET_STATE = 0x200

 PacketHeader = Struct('PacketHeader', [
  ('bodySize', Struct.INT32),
  ('protocolVersion', Struct.INT16),
  ('commandId', Struct.INT16),
  ('responseId', Struct.INT16),
  ('sequenceNumber', Struct.INT16),
  ('reserved', 20),
 ])
 protocolVersion = 0x100

 GetStateResponse = Struct('GetStateResponse', [
  ('currentStateId', Struct.INT16),
 ])

 InitResponse = Struct('InitResponse', [
  ('maxCmdPacketSize', Struct.INT32),
  ('maxResPacketSize', Struct.INT32),
  ('minTimeOut', Struct.INT32),
  ('intervalBeforeCommand', Struct.INT32),
  ('intervalBeforeResponse', Struct.INT32),
 ])

 QueryVersionResponse = Struct('QueryVersionResponse', [
  ('oldFirmMinorVersion', Struct.INT16),
  ('oldFirmMajorVersion', Struct.INT16),
  ('newFirmMinorVersion', Struct.INT16),
  ('newFirmMajorVersion', Struct.INT16),
 ])

 WriteParam = Struct('WriteParam', [
  ('dataNumber', Struct.INT32),
  ('remainingSize', Struct.INT32),
 ])

 WriteResponse = Struct('WriteResponse', [
  ('windowSize', Struct.INT32),
  ('numStatus', Struct.INT32),
 ])

 WriteResponseStatus = Struct('WriteResponseStatus', [
  ('code', Struct.INT16),
 ])

 ERR_OK = 0x1
 ERR_BUSY = 0x2
 ERR_PROV = 0x100
 ERR_SEQUENCE = 0x101
 ERR_PACKET_SIZE = 0x102
 ERR_INVALID_PARAM = 0x103

 STAT_OK = 0x1
 STAT_BUSY = 0x2
 STAT_INVALID_DATA = 0x40
 STAT_LOW_BATTERY = 0x100
 STAT_BAD_BATTERY = 0x101
 STAT_BATTERY_INSERTED = 0x102
 STAT_AC_ADAPTER_REQUIRED = 0x103
 STAT_DISK_INSERTED = 0x120
 STAT_MS_INSERTED = 0x121
 STAT_INVALID_MODEL = 0x140
 STAT_INVALID_REGION = 0x141
 STAT_INVALID_VERSION = 0x142

 BUFFER_SIZE = 512

 def __init__(self, dev):
  self.dev = dev

 def _sendCommand(self, command, data=b'', bufferSize=BUFFER_SIZE):
  commandHeader = self.PacketHeader.pack(
   bodySize = len(data),
   protocolVersion = self.protocolVersion,
   commandId = command,
   responseId = 0,
   sequenceNumber = 0,
  )
  response = self.dev.sendSonyExtCommand(self.SONY_CMD_Updater, commandHeader + data, bufferSize)

  if bufferSize == 0:
   return b''
  responseHeader = self.PacketHeader.unpack(response)
  if responseHeader.responseId != self.ERR_OK:
   if responseHeader.responseId == self.ERR_SEQUENCE:
    raise SonyUpdaterSequenceError()
   raise Exception('Response error: 0x%x' % responseHeader.responseId)
  return response[self.PacketHeader.size:self.PacketHeader.size+responseHeader.bodySize]

 def _sendWriteCommands(self, command, file, size, complete=None):
  i = 0
  written = 0
  windowSize = 0
  completeCalled = False
  while True:
   i += 1
   data = file.read(min(windowSize, size-written))
   written += len(data)
   writeParam = self.WriteParam.pack(dataNumber=i, remainingSize=size-written)
   windowSize, status = self._parseWriteResponse(self._sendCommand(command, writeParam + data))
   if complete and written == size and not completeCalled:
    complete(self.dev)
    completeCalled = True
   if status == [self.STAT_OK]:
    break
   elif status != [self.STAT_BUSY]:
    raise Exception('Firmware update error: ' + ', '.join([self._statusToStr(s) for s in status if s != self.STAT_OK]))

 def _parseWriteResponse(self, data):
  response = self.WriteResponse.unpack(data)
  status = [self.WriteResponseStatus.unpack(data, self.WriteResponse.size+i*self.WriteResponseStatus.size).code for i in range(response.numStatus)]
  return response.windowSize, status

 def _statusToStr(self, status):
  return {
   self.STAT_BUSY: 'Busy',
   self.STAT_INVALID_DATA: 'Invalid data',
   self.STAT_LOW_BATTERY: 'Low battery',
   self.STAT_BAD_BATTERY: 'Bad battery',
   self.STAT_BATTERY_INSERTED: 'Battery inserted',
   self.STAT_AC_ADAPTER_REQUIRED: 'AC adapter required',
   self.STAT_DISK_INSERTED: 'Disk inserted',
   self.STAT_MS_INSERTED: 'Memory card inserted',
   self.STAT_INVALID_MODEL: 'Invalid model',
   self.STAT_INVALID_REGION: 'Invalid region',
   self.STAT_INVALID_VERSION: 'Invalid version',
  }.get(status, 'Unknown (0x%x)' % status)

 def getState(self):
  return self.GetStateResponse.unpack(self._sendCommand(self.CMD_GET_STATE)).currentStateId

 def init(self):
  self.InitResponse.unpack(self._sendCommand(self.CMD_INIT))

 def checkGuard(self, file, size):
  self._sendWriteCommands(self.CMD_CHK_GUARD, file, size)

 def getFirmwareVersion(self):
  response = self.QueryVersionResponse.unpack(self._sendCommand(self.CMD_QUERY_VERSION))
  return (
   '%x.%02x' % (response.oldFirmMajorVersion, response.oldFirmMinorVersion),
   '%x.%02x' % (response.newFirmMajorVersion, response.newFirmMinorVersion),
  )

 def switchMode(self):
  reserved, status = self._parseWriteResponse(self._sendCommand(self.CMD_SWITCH_MODE))
  if status != [self.STAT_OK] and status != [self.STAT_BUSY]:
   raise Exception('Updater mode switch failed')

 def writeFirmware(self, file, size, complete=None):
  self._sendWriteCommands(self.CMD_WRITE_FIRM, file, size, complete)

 def complete(self):
  self._sendCommand(self.CMD_COMPLETE, bufferSize=0)


class SonyAppInstallDevice(SonyUsbDevice, abc.ABC):
 @abc.abstractmethod
 def sendMessage(self, type, data):
  pass

 @abc.abstractmethod
 def receiveMessage(self):
  pass


class SonyMtpAppInstallDevice(MtpDevice, SonyAppInstallDevice):
 # Operation codes (defined in libUsbAppDlSvr.so)
 PTP_OC_GetProxyMessageInfo = 0x9488
 PTP_OC_GetProxyMessage = 0x9489
 PTP_OC_SendProxyMessageInfo = 0x948c
 PTP_OC_SendProxyMessage = 0x948d
 PTP_OC_GetDeviceCapability = 0x940a

 PTP_RC_NoData = 0xa488
 PTP_RC_SonyDeviceBusy = 0xa489
 PTP_RC_InternalError = 0xa806
 PTP_RC_TooMuchData = 0xa809

 InfoMsgHeader = Struct('InfoMsgHeader', [
  ('', 4),# read: 0x10000 / write: 0
  ('magic', Struct.INT16),
  ('', 2),# 0
  ('dataSize', Struct.INT32),
  ('', 2),# read: 0x3000 / write: 0
  ('padding', 42),
 ], Struct.LITTLE_ENDIAN)
 InfoMsgHeaderMagic = 0xb481

 MsgHeader = Struct('MsgHeader', [
  ('type', Struct.INT16),
 ], Struct.BIG_ENDIAN)

 def _write(self, data):
  info = self.InfoMsgHeader.pack(magic=self.InfoMsgHeaderMagic, dataSize=len(data))

  response = self.PTP_RC_SonyDeviceBusy
  while response == self.PTP_RC_SonyDeviceBusy:
   response = self.driver.sendWriteCommand(self.PTP_OC_SendProxyMessageInfo, [], info)
  self._checkResponse(response)

  response = self.PTP_RC_SonyDeviceBusy
  while response == self.PTP_RC_SonyDeviceBusy:
   response = self.driver.sendWriteCommand(self.PTP_OC_SendProxyMessage, [], data)
  self._checkResponse(response)

 def _read(self):
  response, data = self.driver.sendReadCommand(self.PTP_OC_GetProxyMessageInfo, [0])
  self._checkResponse(response)
  info = self.InfoMsgHeader.unpack(data)
  if info.magic != self.InfoMsgHeaderMagic:
   raise Exception('Wrong magic')

  response, data = self.driver.sendReadCommand(self.PTP_OC_GetProxyMessage, [0])
  self._checkResponse(response, [self.PTP_RC_NoData])
  return data[:info.dataSize]

 def sendMessage(self, type, data):
  self._write(self.MsgHeader.pack(type=type) + data)

 def receiveMessage(self):
  data = self._read()
  if data == b'':
   return None, None

  type = self.MsgHeader.unpack(data).type
  data = data[self.MsgHeader.size:]
  return type, data


class SonyAppInstallCamera(object):
 """Methods to communicate a camera in app installation mode"""

 SONY_MSG_Common = 0
 SONY_MSG_Common_Start = 0x400
 SONY_MSG_Common_Hello = 0x401
 SONY_MSG_Common_Bye = 0x402

 SONY_MSG_Tcp = 1
 SONY_MSG_Tcp_ProxyConnect = 0x501
 SONY_MSG_Tcp_ProxyDisconnect = 0x502
 SONY_MSG_Tcp_ProxyData = 0x503
 SONY_MSG_Tcp_ProxyEnd = 0x504

 SONY_MSG_Rest = 2
 SONY_MSG_Rest_In = 0
 SONY_MSG_Rest_Out = 2# anything != 0

 CommonMsgHeader = Struct('CommonMsgHeader', [
  ('version', Struct.INT16),
  ('type', Struct.INT32),
  ('size', Struct.INT32),
  ('padding', 6),
 ], Struct.BIG_ENDIAN)
 CommonMsgVersion = 1

 TcpMsgHeader = Struct('TcpMsgHeader', [
  ('socketFd', Struct.INT32),
 ], Struct.BIG_ENDIAN)

 RestMsgHeader = Struct('RestMsgHeader', [
  ('type', Struct.INT16),
  ('size', Struct.INT16),
 ], Struct.BIG_ENDIAN)

 ProxyConnectMsgHeader = Struct('ProxyConnectMsgHeader', [
  ('port', Struct.INT16),
  ('hostSize', Struct.INT32),
 ], Struct.BIG_ENDIAN)

 SslDataMsgHeader = Struct('SslDataMsgHeader', [
  ('size', Struct.INT32),
 ], Struct.BIG_ENDIAN)

 ProtocolMsgHeader = Struct('ProtocolMsgHeader', [
  ('numProtocols', Struct.INT32),
 ], Struct.BIG_ENDIAN)

 ProtocolMsgProto = Struct('ProtocolMsgProto', [
  ('name', Struct.STR % 4),
  ('id', Struct.INT16),
 ], Struct.BIG_ENDIAN)
 ProtocolMsgProtos = [(b'TCPT', 0x01), (b'REST', 0x100)]

 ThreeValueMsg = Struct('ThreeValueMsg', [
  ('a', Struct.INT16),
  ('b', Struct.INT32),
  ('c', Struct.INT32),
 ], Struct.BIG_ENDIAN)

 def __init__(self, dev):
  self.dev = dev

 def receive(self):
  """Receives and parses the next message from the camera"""
  type, data = self.dev.receiveMessage()
  if type is None:
   return None

  if type == self.SONY_MSG_Common:
   header = self.CommonMsgHeader.unpack(data)
   data = data[self.CommonMsgHeader.size:header.size]
   if header.type == self.SONY_MSG_Common_Hello:
    n = self.ProtocolMsgHeader.unpack(data).numProtocols
    protos = (self.ProtocolMsgProto.unpack(data, self.ProtocolMsgHeader.size+i*self.ProtocolMsgProto.size) for i in range(n))
    return InitResponseMessage([(p.name, p.id) for p in protos])
   elif header.type == self.SONY_MSG_Common_Bye:
    raise Exception('Bye from camera')
   else:
    raise Exception('Unknown common message type: 0x%x' % header.type)

  elif type == self.SONY_MSG_Tcp:
   header = self.CommonMsgHeader.unpack(data)
   data = data[self.CommonMsgHeader.size:header.size]
   tcpHeader = self.TcpMsgHeader.unpack(data)
   data = data[self.TcpMsgHeader.size:]
   if header.type == self.SONY_MSG_Tcp_ProxyConnect:
    proxy = self.ProxyConnectMsgHeader.unpack(data)
    host = data[self.ProxyConnectMsgHeader.size:self.ProxyConnectMsgHeader.size+proxy.hostSize]
    return SslStartMessage(tcpHeader.socketFd, host.decode('latin1'), proxy.port)
   elif header.type == self.SONY_MSG_Tcp_ProxyDisconnect:
    return SslEndMessage(tcpHeader.socketFd)
   elif header.type == self.SONY_MSG_Tcp_ProxyData:
    size = self.SslDataMsgHeader.unpack(data).size
    return SslSendDataMessage(tcpHeader.socketFd, data[self.SslDataMsgHeader.size:self.SslDataMsgHeader.size+size])
   else:
    raise Exception('Unknown tcp message type: 0x%x' % header.type)

  elif type == self.SONY_MSG_Rest:
   header = self.RestMsgHeader.unpack(data)
   data = data[self.RestMsgHeader.size:self.RestMsgHeader.size+header.size]
   if header.type == self.SONY_MSG_Rest_Out:
    return ResponseMessage(data)
   elif header.type == self.SONY_MSG_Rest_In:
    return RequestMessage(data)
   else:
    raise Exception('Unknown rest message type: 0x%x' % header.type)

  else:
   raise Exception('Unknown message type: 0x%x' % type)

 def _receiveResponse(self, type):
  msg = None
  while msg is None:
   msg = self.receive()
  if not isinstance(msg, type):
   raise Exception('Wrong response: %s' % str(msg))
  return msg

 def _sendCommonMessage(self, subType, data, type=SONY_MSG_Common):
  self.dev.sendMessage(type, self.CommonMsgHeader.pack(
   version = self.CommonMsgVersion,
   type = subType,
   size = self.CommonMsgHeader.size + len(data)
  ) + data)

 def _sendTcpMessage(self, subType, socketFd, data):
  self._sendCommonMessage(subType, self.TcpMsgHeader.pack(socketFd=socketFd) + data, self.SONY_MSG_Tcp)

 def _sendRestMessage(self, subType, data):
  self.dev.sendMessage(self.SONY_MSG_Rest, self.RestMsgHeader.pack(type=subType, size=len(data)) + data)

 def emptyBuffer(self):
  """Receives and discards all pending messages from the camera"""
  msg = True
  while msg:
   msg = self.receive()

 def sendInit(self, protocols=ProtocolMsgProtos):
  """Send an initialization message to the camera"""
  data = self.ProtocolMsgHeader.pack(numProtocols=len(protocols))
  for name, id in protocols:
   data += self.ProtocolMsgProto.pack(name=name, id=id)
  self._sendCommonMessage(self.SONY_MSG_Common_Start, data)
  return self._receiveResponse(InitResponseMessage).protocols

 def sendRequest(self, data):
  """Sends a REST request to the camera. Used to start communication"""
  self._sendRestMessage(self.SONY_MSG_Rest_Out, data)
  return self._receiveResponse(ResponseMessage).data

 def sendSslData(self, req, data):
  """Sends raw SSL response data to the camera"""
  self._sendTcpMessage(self.SONY_MSG_Tcp_ProxyData, req, self.SslDataMsgHeader.pack(size=len(data)) + data)

 def sendSslEnd(self, req):
  """Lets the camera know that the SSL socket has been closed"""
  self._sendTcpMessage(self.SONY_MSG_Tcp_ProxyEnd, req, self.ThreeValueMsg.pack(a=1, b=1, c=0))

 def sendEnd(self):
  """Ends the communication with the camera"""
  self._sendCommonMessage(self.SONY_MSG_Common_Bye, self.ThreeValueMsg.pack(a=0, b=0, c=0))


class SonySenserDevice(SonyUsbDevice):
 SenserPacketHeader = Struct('SenserPacketHeader', [
  ('size', Struct.INT32),
  ('pFunc', Struct.INT16),
  ('sequence', Struct.INT16),
  ('version', Struct.INT8),
  ('miconType', Struct.INT8),
  ('offsetType', Struct.INT8),
  ('response', Struct.INT8),
 ])

 SenserMinSize = 0x200
 SenserChunkSize = 0x8000
 SenserMaxSize = 0x100000

 def __init__(self, driver):
  super(SonySenserDevice, self).__init__(driver)
  self._sequence = 1

 def sendSenserPacket(self, pFunc, data, oData=None):
  while data != b'':
   header = self.SenserPacketHeader.pack(size=len(data), pFunc=pFunc, sequence=self._sequence, version=0, miconType=0, offsetType=0, response=0)
   self.driver.write(header + data[:self.SenserMaxSize])
   data = data[self.SenserMaxSize:]

  outData = BytesIO() if oData is None else oData
  minSize = 0 if self.driver.getId()[1] == 0x0336 else self.SenserMinSize
  while True:
   l = max(minSize - self.SenserPacketHeader.size, 0)
   d = self.driver.read(self.SenserPacketHeader.size + l)
   header = self.SenserPacketHeader.unpack(d)
   if header.sequence != self._sequence:
    raise Exception('Wrong senser sequence')
   outData.write(d[self.SenserPacketHeader.size:])
   done = l

   dataLen = min(header.size, self.SenserMaxSize)
   chunkLen = self.SenserChunkSize - minSize
   while done < dataLen:
    l = min(dataLen - done, chunkLen)
    outData.write(self.driver.read(l))
    done += l
    if not (l & (self.SenserMinSize - 1)):
     self.driver.read(self.SenserMinSize)
    chunkLen = self.SenserChunkSize
   if header.size <= self.SenserMaxSize:
    break
  self._sequence += 1
  return header.response, outData.getvalue() if oData is None else None

 def readTerminal(self):
  try:
   return self.driver.read(0x40, ep=1, timeout=100)
  except GenericUsbException:
   return b''

 def writeTerminal(self, data):
  while data:
   self.driver.write(data[:0x40], ep=1)
   data = data[0x40:]


class SonySenserAuthDevice(SonyUsbDevice):
 SONY_VendorRequest_StartSenser = (1, 0x37ff, 0xd7aa)
 SONY_VendorRequest_StopSenser = (1, 0xc800, 0x2855)

 AuthPacket = Struct('AuthPacket', [
  ('cmd', Struct.INT16),
  ('salt', Struct.INT16),
  ('data', Struct.STR % 0x200),
 ], Struct.BIG_ENDIAN)

 def start(self):
  try:
   self.driver.vendorRequestOut(*self.SONY_VendorRequest_StartSenser)
  except GenericUsbException:
   pass

 def stop(self):
  try:
   self.driver.vendorRequestOut(*self.SONY_VendorRequest_StopSenser)
  except GenericUsbException:
   pass

 def _sendAuthPacket(self, cmd, data=b''):
  self.driver.write(self.AuthPacket.pack(cmd=~cmd & 0xffff, salt=0, data=data))
  response = self.AuthPacket.unpack(self.driver.read(self.AuthPacket.size))
  ret = (~response.cmd & 0xffff) - response.salt
  return ret, response.data

 def authenticate(self):
  for i in range(3):
   ret, data = self._sendAuthPacket(1)
   if ret not in [2, 8]:
    raise Exception('Invalid response: %d' % ret)

   keys = constants.senserKeysSha1 if ret == 2 else constants.senserKeysSha256
   data = data + keys[i] if self.driver.getId()[1] == 0x0336 else data[:4]
   hash = crypto.sha1_faulty(data) if ret == 2 else SHA256.new(data).digest()
   ret, data = self._sendAuthPacket(3, dump8(1) + hash)
   if ret != 4:
    raise Exception('Invalid response: %d' % ret)

  ret, data = self._sendAuthPacket(5)
  if ret != 6:
   raise Exception('Invalid response: %d' % ret)
  res = parse8(data[:1])
  if res != 1:
   raise Exception('Senser error %d' % res)


class SonySenserCamera(object):
 SONY_PFUNC_ProductInfo = 0x10
 SONY_PFUNC_FirmwareUpdate = 0x20
 SONY_PFUNC_MiconAccess = 0x30
 SONY_PFUNC_AdjustControl = 0x40
 SONY_PFUNC_TestMode = 0xff00
 SONY_PFUNC_FileControl = 0xff01
 SONY_PFUNC_Sonar = 0xff02
 SONY_PFUNC_MemoryDump = 0xff03

 CommandHeader = Struct('CommandHeader', [
  ('category', Struct.INT16),
  ('command', Struct.INT16),
 ])

 FileControlHeader = Struct('FileControlHeader', [
  ('cmd', Struct.INT16),
  ('filenameSize', Struct.INT16),
 ])

 MemoryDumpHeader = Struct('MemoryDumpHeader', [
  ('base', Struct.INT32),
  ('size', Struct.INT32),
 ])

 SONY_PRODUCT_INFO_READ_HASP = (0, 0x001f)

 SONY_FILE_CONTROL_WRITE = 1
 SONY_FILE_CONTROL_READ = 2
 SONY_FILE_CONTROL_DELETE = 3

 def __init__(self, dev):
  self.dev = dev

 def _sendProductInfoPacket(self, category, command, data=b''):
  header = self.CommandHeader.pack(category=category, command=command)
  res, data = self.dev.sendSenserPacket(self.SONY_PFUNC_ProductInfo, header + data)
  if res != 1:
   raise Exception('Senser product info error %d' % res)
  return data

 def _sendAdjustControlPacket(self, block, code, data=b''):
  header = self.CommandHeader.pack(category=block, command=code)
  res, data = self.dev.sendSenserPacket(self.SONY_PFUNC_AdjustControl, header + data)
  if res != 0:
   raise Exception('Senser adjust control error %d' % res)
  return data

 def _sendFileControlPacket(self, cmd, filename, data=b'', outFile=None):
  filename = filename.encode('latin1')
  filename += b'\0' * (4 - len(filename) % 4)
  header = self.FileControlHeader.pack(cmd=cmd, filenameSize=len(filename))
  res, data = self.dev.sendSenserPacket(self.SONY_PFUNC_FileControl, header + filename + data, outFile)
  if res != 1:
   raise Exception('Senser file control error %d' % res)
  return data

 def _sendMemoryDumpPacket(self, base, size, data=b'', outFile=None):
  header = self.MemoryDumpHeader.pack(base=base, size=size)
  res, data = self.dev.sendSenserPacket(self.SONY_PFUNC_MemoryDump, header + data, outFile)
  if res not in [0, 1]:
   raise Exception('Senser memory dump error %d' % res)
  return data

 def readHasp(self):
  return self._sendProductInfoPacket(*self.SONY_PRODUCT_INFO_READ_HASP, dump8(0))

 def readFile(self, filename, outFile=None):
  return self._sendFileControlPacket(self.SONY_FILE_CONTROL_READ, filename, b'', outFile)

 def writeFile(self, filename, data):
  self._sendFileControlPacket(self.SONY_FILE_CONTROL_WRITE, filename, data)

 def deleteFile(self, filename):
  self._sendFileControlPacket(self.SONY_FILE_CONTROL_DELETE, filename)

 def readMemory(self, base, size, outFile=None):
  return self._sendMemoryDumpPacket(base, size, b'', outFile)

 def writeMemory(self, base, data):
  self._sendMemoryDumpPacket(base, len(data), data)

 def setTerminalEnable(self, enable):
  self._sendProductInfoPacket(0, 0xf1, dump8(1 if enable else 0))
  try:
   self._sendAdjustControlPacket(0x601, 0x1f, dump8(2 if enable else 0))
  except:
   pass
