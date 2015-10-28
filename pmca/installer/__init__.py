"""Manages the communication between camera, PC and appengine website during app installation"""

from collections import namedtuple
import json
import select
import socket

from ..usb.sony import *
from .. import xpd

Response = namedtuple('Response', 'protocol, code, status, headers, data')
Request = namedtuple('Request', 'protocol, method, url, headers, data')

Status = namedtuple('Status', 'code, message, percent, totalSize')
Result = namedtuple('Result', 'code, message')

def _buildRequest(endpoint, contentType, data):
 return 'POST %s REST/1.0\r\nContent-type: %s\r\n\r\n%s' % (endpoint, contentType, data)

def _parseHttp(data):
 headers, data = data.split('\r\n\r\n')[:2]
 headers = headers.split('\r\n')
 firstLine = headers[0]
 headers = dict(h.split(': ') for h in headers[1:])
 return firstLine, headers, data

def _parseRequest(data):
 firstLine, headers, data = _parseHttp(data)
 method, url, protocol = firstLine.split(' ', 2)
 return Request(protocol, method, url, headers, data)

def _parseResponse(data):
 firstLine, headers, data = _parseHttp(data)
 protocol, code, status = firstLine.split(' ', 2)
 return Response(protocol, int(code), status, headers, data)

def _parseResult(data):
 data = json.loads(data)
 return Result(data['resultCode'], data['message'])

def _parseStatus(data):
 data = json.loads(data)
 return Status(data['status'], data['status text'], data['percent'], data['total size'])

def install(dev, xpdData, statusFunc = None):
 """Sends an xpd file to the camera, lets it access the internet through SSL, waits for the response"""
 # Initialize communication
 dev.emptyBuffer()
 dev.sendInit()

 # Start the installatin by sending the xpd data in a REST request
 response = dev.sendRequest(_buildRequest('/task/start', xpd.constants.mimeType, xpdData))
 response = _parseResponse(response)
 result = _parseResult(response.data)
 if result.code != 0:
  raise Exception('Response error %s' % str(result))

 connectionId = 0
 sock = None

 # Main loop
 while True:
  if sock != None:
   ready = select.select([sock], [], [], 0)
   if ready[0]:
    # There is data waiting on the socket, let's send it to the camera
    resp = sock.recv(4096)
    if resp != '':
     dev.sendSslData(connectionId, resp)
    else:
     dev.sendSslEnd(connectionId)
     sock.close()
     sock = None

  # Receive the next message from the camera
  message = dev.receive()
  if message == None:
   # Nothing received, let's wait
   continue

  if isinstance(message, SslStartMessage):
   # The camera wants us to open an SSL socket
   connectionId = message.connectionId
   sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   sock.connect((message.host, 443))
  elif isinstance(message, SslSendDataMessage) and sock and message.connectionId == connectionId:
   # The camera wants to send data over the socket
   sock.send(message.data)
  elif isinstance(message, RequestMessage):
   # The camera sends a REST message
   request = _parseRequest(message.data)
   if request.url == '/task/progress':
    # Progress
    status = _parseStatus(request.data)
    if statusFunc:
     statusFunc(status)
   elif request.url == '/task/complete':
    # The camera completed the task, let's stop this loop
    result = _parseResult(request.data)
    dev.sendEnd()
    return result
   else:
    raise Exception("Unknown message url %s" % request.url)
  else:
   raise Exception("Unknown message %s" % str(message))
