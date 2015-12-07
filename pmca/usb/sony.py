"""Methods to communicate with Sony MTP devices"""

from collections import namedtuple

from . import *
from ..util import *

ResponseMessage = namedtuple('ResponseMessage', 'data')
RequestMessage = namedtuple('RequestMessage', 'data')
InitResponseMessage = namedtuple('InitResponseMessage', 'data')
SslStartMessage = namedtuple('SslStartMessage', 'connectionId, host')
SslSendDataMessage = namedtuple('SslSendDataMessage', 'connectionId, data')
SslEndMessage = namedtuple('SslEndMessage', 'connectionId')

SONY_ID_VENDOR = 0x054c

CMD_ID_SWITCH = 0x9280
CMD_ID_WRITE1 = 0x948c
CMD_ID_WRITE2 = 0x948d
CMD_ID_READ1 = 0x9488
CMD_ID_READ2 = 0x9489


def isSonyMtpCamera(info):
 """Pass an MTP device info tuple. Guesses if the device is a camera in MTP mode."""
 return info.vendorExtension == '' and set([CMD_ID_SWITCH]) <= info.operationsSupported

def isSonyMtpAppInstaller(info):
 """Pass an MTP device info tuple. Guesses if the device is a camera in app installation mode."""
 return 'sony.net/SEN_PRXY_MSG:' in info.vendorExtension and set([CMD_ID_WRITE1, CMD_ID_WRITE2, CMD_ID_READ1, CMD_ID_READ2]) <= info.operationsSupported


class SonyMtpCamera(MtpDevice):
 """Methods to communicate a camera in MTP mode"""
 def switchToAppInstaller(self):
  """Tells the camera to switch to app installation mode"""
  response = self.driver.sendWriteCommand(CMD_ID_SWITCH, [5], 4*'\x00' + '\x02\x00\x00\x00' + 8*'\x00')
  self._checkResponse(response)


class SonyMtpAppInstaller(MtpDevice):
 """Methods to communicate a camera in app installation mode"""
 def _write(self, data):
  response = self.driver.sendWriteCommand(CMD_ID_WRITE1, [], 4*'\x00' + '\x81\xb4\x00\x00' + dump32le(len(data)) + 40*'\x00' + '\x02\x41\x00\x00' + 4*'\x00')
  self._checkResponse(response)
  response = self.driver.sendWriteCommand(CMD_ID_WRITE2, [], data)
  self._checkResponse(response)

 def _read(self):
  response, data = self.driver.sendReadCommand(CMD_ID_READ1, [0])
  self._checkResponse(response)
  response, data = self.driver.sendReadCommand(CMD_ID_READ2, [0])
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
