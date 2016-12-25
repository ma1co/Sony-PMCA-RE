"""Methods to communicate with Sony MTP devices"""

import binascii
from collections import namedtuple
from io import BytesIO

from . import *
from ..util import *

CameraInfo = namedtuple('CameraInfo', 'plist, modelName, modelCode, serial')

ResponseMessage = namedtuple('ResponseMessage', 'data')
RequestMessage = namedtuple('RequestMessage', 'data')
InitResponseMessage = namedtuple('InitResponseMessage', 'protocols')
SslStartMessage = namedtuple('SslStartMessage', 'connectionId, host, port')
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

 def _sendCommand(self, cmd, bufferSize=BUFFER_SIZE):
  data = self.dev.sendSonyExtCommand(cmd[0], 4*b'\0' + dump32le(cmd[1]) + 8*b'\0', bufferSize)
  if bufferSize == 0:
   return b''
  size = parse32le(data[:4])
  return data[16:16+size]

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

 def getKikiLog(self):
  """Reads the first part of /tmp/kikilog.dat"""
  self._sendCommand(self.SONY_CMD_KikiLogSender_InitKikiLog)
  kikilog = b''
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
  self._sendCommand(self.SONY_CMD_ScalarExtCmdPlugIn_NotifyScalarDlmode, bufferSize=0)

 def powerOff(self):
  """Forces the camera to turn off"""
  self._sendCommand(self.SONY_CMD_ExtBackupCommunicator_ForcePowerOff, bufferSize=0)


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

 def _sendWriteCommands(self, command, file, size, progress=None):
  i = 0
  written = 0
  windowSize = 0
  while True:
   i += 1
   data = file.read(min(windowSize, size-written))
   written += len(data)
   writeParam = self.WriteParam.pack(dataNumber=i, remainingSize=size-written)
   windowSize, status = self._parseWriteResponse(self._sendCommand(command, writeParam + data))
   if progress:
    progress(written, size)
   if status == [self.STAT_OK]:
    break
   elif status != [self.STAT_BUSY]:
    raise Exception('Firmware update error: ' + ', '.join([self._statusToStr(s) for s in status]))

 def _parseWriteResponse(self, data):
  response = self.WriteResponse.unpack(data)
  status = [self.WriteResponseStatus.unpack(data, self.WriteResponse.size+i*self.WriteResponseStatus.size).code for i in range(response.numStatus)]
  return response.windowSize, status

 def _statusToStr(self, status):
  return {
   self.STAT_INVALID_DATA: 'Invalid data',
   self.STAT_LOW_BATTERY: 'Low battery',
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
  if status != [self.STAT_OK]:
   raise Exception('Updater mode switch failed')

 def writeFirmware(self, file, size, progress=None):
  self._sendWriteCommands(self.CMD_WRITE_FIRM, file, size, progress)

 def complete(self):
  self._sendCommand(self.CMD_COMPLETE, bufferSize=0)


class SonyMtpAppInstaller(MtpDevice):
 """Methods to communicate a camera in app installation mode"""

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
  self.InfoMsgHeader.unpack(data)

  response, data = self.driver.sendReadCommand(self.PTP_OC_GetProxyMessage, [0])
  self._checkResponse(response, [self.PTP_RC_NoData])
  return data

 def receive(self):
  """Receives and parses the next message from the camera"""
  data = self._read()
  if data == b'':
   return None

  type = self.MsgHeader.unpack(data).type
  data = data[self.MsgHeader.size:]

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

 def _sendMessage(self, type, data):
  self._write(self.MsgHeader.pack(type=type) + data)

 def _sendCommonMessage(self, subType, data, type=SONY_MSG_Common):
  self._sendMessage(type, self.CommonMsgHeader.pack(
   version = self.CommonMsgVersion,
   type = subType,
   size = self.CommonMsgHeader.size + len(data)
  ) + data)

 def _sendTcpMessage(self, subType, socketFd, data):
  self._sendCommonMessage(subType, self.TcpMsgHeader.pack(socketFd=socketFd) + data, self.SONY_MSG_Tcp)

 def _sendRestMessage(self, subType, data):
  self._sendMessage(self.SONY_MSG_Rest, self.RestMsgHeader.pack(type=subType, size=len(data)) + data)

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
