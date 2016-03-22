from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import requests
import ssl
from threading import Thread

from . import *
from .. import spk

class BufferedWriter(BytesIO):
 def __init__(self, file):
  BytesIO.__init__(self)
  self.wrappedFile = file

 def flush(self):
  self.wrappedFile.write(self.getvalue())
  self.truncate(0)

 def close(self):
  BytesIO.close(self)
  self.wrappedFile.close()


class HttpHandler(BaseHTTPRequestHandler):
 def setup(self):
  BaseHTTPRequestHandler.setup(self)
  self.wfile = BufferedWriter(self.wfile)# Responses have to be buffered and sent in one go

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


class LocalMarketServer(HTTPServer):
 """A local https server to communicate with the camera"""

 def __init__(self, certFile, apkData=None, host='127.0.0.1', port=443):
  HTTPServer.__init__(self, (host, port), HttpHandler)
  self.url = 'https://' + host + '/'
  self.apkData = apkData
  self.result = None
  self.socket = ssl.wrap_socket(self.socket, certfile=certFile)

 def run(self):
  """Start the local server"""
  thread = Thread(target=self.serve_forever)
  thread.daemon = True
  thread.start()

 def getXpd(self):
  """Return the xpd contents"""
  return getXpdResponse('0', self.url)

 def getResult(self):
  """Return the result sent from the camera"""
  if not self.result:
   raise Exception('Task was not completed')
  return self.result

 def handlePost(self, handler, body):
  """Handle POST requests to the server"""
  if not self.result and self.apkData:
   # Tell the camera to download and install an app
   response = getJsonInstallResponse('app', self.url)
  else:
   response = getJsonResponse()

  self.result = parsePostData(body)# Save the result sent by the camera
  handler.output(constants.jsonMimeType, response)

 def handleGet(self, handler):
  """Handle GET requests to the server"""
  # Send the spk file to the camera
  handler.output(spk.constants.mimeType, spk.dump(self.apkData), 'app%s' % spk.constants.extension)


class RemoteMarketServer:
 """A wrapper for a remote api"""

 def __init__(self, host, apkData=None):
  self.base = 'https://' + host
  self.apkData = apkData

 def run(self):
  """Uploads the apk (if any)"""
  self.taskStartUrl = '/ajax/task/start'
  if self.apkData:
   url = requests.get(self.base + '/ajax/upload').json()['url']
   blobKey = requests.post(url, files={'file': ('app.apk', self.apkData)}).json()['key']
   self.taskStartUrl += '/blob/' + blobKey

 def getXpd(self):
  """Create a new task and download the xpd"""
  self.task = str(requests.get(self.base + self.taskStartUrl).json()['id'])
  return requests.get(self.base + '/camera/xpd/' + self.task).text.encode('ascii','ignore')

 def getResult(self):
  """Return the task result"""
  result = requests.get(self.base + '/ajax/task/get/' + self.task).json()
  if not result['completed']:
   raise Exception('Task was not completed')
  return result['response']

 def shutdown(self):
  pass
