from collections import OrderedDict
from io import BytesIO
import json
import ssl
from threading import Thread

try:
 from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
 # Python 2
 from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from . import *
from .. import appstore
from ..util import http
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

 def __init__(self, repo, certFile, host='127.0.0.1', port=4443):
  HTTPServer.__init__(self, (host, port), HttpHandler)
  self.host = host
  self.port = port
  self.url = 'https://' + host + '/'
  self.appstore = appstore.AppStore(repo)
  self.apk = None
  self.result = None
  self.socket = ssl.wrap_socket(self.socket, certfile=certFile)

 def listApps(self):
  return self.appstore.apps

 def startup(self):
  """Start the local server"""
  thread = Thread(target=self.serve_forever)
  thread.daemon = True
  thread.start()

 def setApk(self, apkName, apkData):
  self.apk = apkData

 def setApp(self, package):
  self.setApk(None, self.appstore.apps[package].release.asset)

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


class RemoteMarketServer(object):
 """A wrapper for a remote api"""

 def __init__(self, host, port=443):
  self.host = host
  self.port = port
  self.base = 'https://' + host
  self.taskStartUrl = ''
  self.task = None

 def listApps(self):
  apps = (appstore.App(None, dict) for dict in json.loads(http.get(self.base + '/api/apps').data))
  return OrderedDict((app.package, app) for app in apps)

 def startup(self):
  pass

 def setApk(self, apkName, apkData):
  """Uploads the apk (if any)"""
  url = json.loads(http.get(self.base + '/ajax/upload').data)['url']
  blobKey = json.loads(http.postFile(url, apkName, apkData).data)['key']
  self.taskStartUrl = '/blob/' + blobKey

 def setApp(self, package):
  self.taskStartUrl = '/app/' + package

 def getXpd(self):
  """Create a new task and download the xpd"""
  self.task = str(json.loads(http.get(self.base + '/ajax/task/start' + self.taskStartUrl).data)['id'])
  return http.get(self.base + '/camera/xpd/' + self.task).raw_data

 def getResult(self):
  """Return the task result"""
  if not self.task:
   raise Exception('Task was not started')
  result = json.loads(http.get(self.base + '/ajax/task/get/' + self.task).data)
  if not result['completed']:
   raise Exception('Task was not completed')
  return result['response']

 def shutdown(self):
  pass


class ServerContext(object):
 """Use this in a with statement"""
 def __init__(self, server):
  self._server = server

 def __enter__(self):
  self._server.startup()
  return self._server

 def __exit__(self, type, value, traceback):
  self._server.shutdown()
