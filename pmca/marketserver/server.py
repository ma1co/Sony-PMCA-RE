import contextlib
from http.server import BaseHTTPRequestHandler
from socketserver import TCPServer
from threading import Thread
import tlslite

from . import *
from .. import spk


class HttpHandler(BaseHTTPRequestHandler):
 rbufsize = -1
 wbufsize = -1

 def log_request(self, code='-', size='-'):
  pass

 def output(self, mimeType, data, filename=None):
  self.send_response(200)
  self.send_header('Connection', 'Keep-Alive')
  self.send_header('Content-Type', mimeType)
  self.send_header('Content-Length', len(data))
  if filename:
   self.send_header('Content-Disposition', 'attachment;filename="%s"' % filename)
  self.end_headers()
  self.wfile.write(data)

 def do_POST(self):
  self.server.handlePost(self, self.rfile.read(int(self.headers['Content-Length'])))

 def do_GET(self):
  self.server.handleGet(self)


class TLSConnection(tlslite.TLSConnection):
 def recv_into(self, b):
  return super(TLSConnection, self).recv_into(b) or 0


class LocalMarketServer(TCPServer):
 """A local https server to communicate with the camera"""
 allow_reuse_address = True

 def __init__(self, certFile, host='127.0.0.1', port=4443):
  super(LocalMarketServer, self).__init__((host, port), HttpHandler)
  self.url = 'https://' + host + '/'
  self.apk = None
  self.result = None

  with open(certFile) as f:
   cert = f.read()
  self.certChain = tlslite.X509CertChain()
  self.certChain.parsePemList(cert)
  self.privateKey = tlslite.parsePEMKey(cert, private=True)

 def finish_request(self, sock, client_address):
  sock = TLSConnection(sock)
  sock.handshakeServer(certChain=self.certChain, privateKey=self.privateKey)
  super(LocalMarketServer, self).finish_request(sock, client_address)
  sock.close()

 def startup(self):
  """Start the local server"""
  thread = Thread(target=self.serve_forever)
  thread.daemon = True
  thread.start()

 def setApk(self, apkData):
  self.apk = apkData

 def getXpd(self):
  """Return the xpd contents"""
  return getXpdResponse('0', constants.baseUrl)

 def getResult(self):
  """Return the result sent from the camera"""
  if not self.result:
   raise Exception('Task was not completed')
  return self.result

 def handlePost(self, handler, body):
  """Handle POST requests to the server"""
  if not self.result and self.apk:
   # Tell the camera to download and install an app
   response = getJsonInstallResponse('app', self.url)
  else:
   response = getJsonResponse()

  self.result = parsePostData(body)# Save the result sent by the camera
  handler.output(constants.jsonMimeType, response)

 def handleGet(self, handler):
  """Handle GET requests to the server"""
  # Send the spk file to the camera
  handler.output(spk.constants.mimeType, spk.dump(self.apk), 'app%s' % spk.constants.extension)


class ServerContext(contextlib.AbstractContextManager):
 """Use this in a with statement"""
 def __init__(self, server):
  self._server = server

 def __enter__(self):
  self._server.startup()
  return self._server

 def __exit__(self, type, value, traceback):
  self._server.shutdown()
