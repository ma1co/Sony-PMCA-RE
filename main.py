"""A Google appengine application which allows you to download apps from the PMCA store and to install custom apps on your camera"""

import datetime
import jinja2
import json
import re
import webapp2
import yaml

from google.appengine.api import urlfetch
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers

from pmca import marketclient
from pmca import marketserver
from pmca import spk
from pmca import xpd


class Task(ndb.Model):
 """The Entity used to save task data in the datastore between requests"""
 blob = ndb.BlobKeyProperty()
 app = ndb.StringProperty()
 date = ndb.DateTimeProperty(auto_now_add = True)
 completed = ndb.BooleanProperty(default = False)
 response = ndb.TextProperty()


class BaseHandler(webapp2.RequestHandler):
 def json(self, data):
  """Outputs the given dict as JSON"""
  self.output('application/json', json.dumps(data))

 def template(self, name, data = {}):
  """Renders a jinja2 template"""
  self.response.write(jinjaEnv.get_template(name).render(data))

 def output(self, mimeType, data, filename = None):
  """Outputs a file with the given mimetype"""
  self.response.content_type = mimeType
  if filename:
   self.response.headers['Content-Disposition'] = 'attachment;filename="%s"' % filename
  self.response.write(data)

 def appConfig(self):
  with open('config_apps.yaml', 'r') as f:
   return yaml.load(f)


class HomeHandler(BaseHandler):
 """Displays the home page"""
 def get(self):
  self.template('home.html')


class ApkUploadHandler(BaseHandler, blobstore_handlers.BlobstoreUploadHandler):
 """Handles the upload of apk files to Google appengine"""
 def get(self):
  self.template('apk/upload.html', {
   'uploadUrl': blobstore.create_upload_url(self.uri_for('apkUpload')),
  })

 def post(self):
  uploads = self.get_uploads()
  if len(uploads) == 1:
   return self.redirect_to('blobPlugin', blobKey = uploads[0].key())
  self.get()


class PluginHandler(BaseHandler):
 """Displays the page to start a new USB task sequence"""
 def get(self, args = {}):
  self.template('plugin/start.html', args)

 def getBlob(self, blobKey):
  blob = blobstore.get(blobKey)
  if not blob:
   return self.error(404)
  self.get({'blob': blob})

 def getApp(self, appId):
  config = self.appConfig()
  if not appId in config['apps']:
   return self.error(404)
  self.get({'appId': appId, 'app': config['apps'][appId]})


class PluginInstallHandler(BaseHandler):
 """Displays the help text to install the PMCA Downloader plugin"""
 def get(self):
  self.template('plugin/install.html', {
   'text': marketclient.getPluginInstallText(),
  })


class TaskStartHandler(BaseHandler):
 """Creates a new task sequence and returns its id"""
 def get(self, task = Task()):
  taskId = task.put().id()
  self.json({'id': taskId})

 def getBlob(self, blobKey):
  blob = blobstore.get(blobKey)
  if not blob:
   return self.error(404)
  self.get(Task(blob = blob.key()))

 def getApp(self, appId):
  if not appId in self.appConfig()['apps']:
   return self.error(404)
  self.get(Task(app = appId))


class TaskViewHandler(BaseHandler):
 """Displays the result of the given task sequence (called over AJAX)"""
 def get(self, taskKey):
  task = ndb.Key(Task, int(taskKey)).get()
  if not task:
   return self.error(404)
  self.template('task/view.html', {
   'completed': task.completed,
   'response': marketserver.parsePostData(task.response) if task.completed else None,
  })


class XpdHandler(BaseHandler):
 """Returns the xpd file corresponding to the given task sequence (called by the plugin)"""
 def get(self, taskKey):
  task = ndb.Key(Task, int(taskKey)).get()
  if not task:
   return self.error(404)
  xpdData = marketserver.getXpdResponse(task.key.id(), self.uri_for('portal', _full = True))
  self.output(xpd.constants.mimeType, xpdData)


class PortalHandler(BaseHandler):
 """Saves the data sent by the camera to the datastore and returns the actions to be taken next (called by the camera)"""
 def post(self):
  data = self.request.body
  taskKey = int(marketserver.parsePostData(data)['session']['correlationid'])
  task = ndb.Key(Task, taskKey).get()
  if not task:
   return self.error(404)
  if not task.completed and task.blob:
   response = marketserver.getJsonInstallResponse('App', self.uri_for('blobSpk', blobKey = task.blob, _full = True))
  elif not task.completed and task.app:
   response = marketserver.getJsonInstallResponse('App', self.uri_for('appSpk', appId = task.app, _full = True))
  else:
   response = marketserver.getJsonResponse()
  task.completed = True
  task.response = data
  task.put()
  self.output(marketserver.constants.jsonMimeType, response)


class SpkHandler(BaseHandler):
 """Returns an spk file containing an apk file"""
 def get(self, apkData):
  spkData = spk.dump(apkData)
  self.output(spk.constants.mimeType, spkData, "app%s" % spk.constants.extension)

 def getBlob(self, blobKey):
  blob = blobstore.get(blobKey)
  if not blob:
   return self.error(404)
  with blob.open() as f:
   apkData = f.read()
  self.get(apkData)

 def getApp(self, appId):
  config = self.appConfig()
  if not appId in config['apps']:
   return self.error(404)
  githubUrl = 'https://api.github.com/repos/%s/releases/latest?client_id=%s&client_secret=%s' % (config['apps'][appId]['repo'], config['github']['clientId'], config['github']['clientSecret'])
  github = json.loads(urlfetch.fetch(githubUrl).content)
  apkData = urlfetch.fetch(github['assets'][0]['browser_download_url']).content
  self.get(apkData)


class MarketLoginHandler(BaseHandler):
 """Manages the login to the PMCA store"""
 def get(self):
  self.template('market/login.html', {
   'registerUrl': marketclient.constants.registerUrl,
  })

 def post(self):
  email = self.request.get('email')
  password = self.request.get('password')
  if email and password:
   portalid = marketclient.login(email, password)
   if portalid:
    return self.redirect_to('marketDevices', portalid = portalid)
  self.get()


class MarketDevicesHandler(BaseHandler):
 """Manages the selection of a device from the PMCA account"""
 def get(self, portalid):
  self.template('market/devices.html', {
   'devices': marketclient.getDevices(portalid),
   'portalid': portalid,
  })


class MarketAppsHandler(BaseHandler):
 """Displays all apps from the PMCA store available for the given device"""
 def get(self, portalid, deviceid):
  self.template('market/apps.html', {
   'apps': [app for app in marketclient.getApps(deviceid) if not app['status'].startswith('$')],
   'portalid': portalid,
   'deviceid': deviceid,
  })


class MarketDownloadHandler(BaseHandler):
 """Downloads and decrypts an app from the PMCA store"""
 def get(self, portalid, deviceid, appid):
  spkName, spkData = marketclient.download(portalid, deviceid, appid)
  apkData = spk.parse(spkData)
  apkName = re.sub('(%s)?$' % re.escape(spk.constants.extension), '.apk', spkName)
  self.output('application/vnd.android.package-archive', apkData, apkName)


class AppsHandler(BaseHandler):
 """Displays apps available on github"""
 def get(self):
  self.template('apps/list.html', {
   'apps': self.appConfig()['apps'],
  })


class CleanupHandler(BaseHandler):
 """Deletes all data older than one hour"""
 keepForMinutes = 60
 def get(self):
  deleteBeforeDate = datetime.datetime.now() - datetime.timedelta(minutes = self.keepForMinutes)
  for blob in blobstore.BlobInfo.gql('WHERE creation < :1', deleteBeforeDate):
   blob.delete()
  ndb.delete_multi(Task.gql('WHERE date < :1', deleteBeforeDate).fetch(keys_only = True))


app = webapp2.WSGIApplication([
 webapp2.Route('/', HomeHandler, 'home'),
 webapp2.Route('/upload', ApkUploadHandler, 'apkUpload'),
 webapp2.Route('/plugin', PluginHandler, 'plugin'),
 webapp2.Route('/plugin/blob/<blobKey>', PluginHandler, 'blobPlugin', handler_method = 'getBlob'),
 webapp2.Route('/plugin/app/<appId>', PluginHandler, 'appPlugin', handler_method = 'getApp'),
 webapp2.Route('/plugin/install', PluginInstallHandler, 'installPlugin'),
 webapp2.Route('/ajax/task/start', TaskStartHandler, 'taskStart'),
 webapp2.Route('/ajax/task/start/blob/<blobKey>', TaskStartHandler, 'blobTaskStart', handler_method = 'getBlob'),
 webapp2.Route('/ajax/task/start/app/<appId>', TaskStartHandler, 'appTaskStart', handler_method = 'getApp'),
 webapp2.Route('/ajax/task/view/<taskKey>', TaskViewHandler, 'taskView'),
 webapp2.Route('/camera/xpd/<taskKey>', XpdHandler, 'xpd'),
 webapp2.Route('/camera/portal', PortalHandler, 'portal'),
 webapp2.Route('/camera/spk/blob/<blobKey>', SpkHandler, 'blobSpk', handler_method = 'getBlob'),
 webapp2.Route('/camera/spk/app/<appId>', SpkHandler, 'appSpk', handler_method = 'getApp'),
 webapp2.Route('/market', MarketLoginHandler, 'marketLogin'),
 webapp2.Route('/market/<portalid>', MarketDevicesHandler, 'marketDevices'),
 webapp2.Route('/market/<portalid>/<deviceid>', MarketAppsHandler, 'marketApps'),
 webapp2.Route('/market/<portalid>/<deviceid>/<appid>', MarketDownloadHandler, 'marketDownload'),
 webapp2.Route('/apps', AppsHandler, 'apps'),
 webapp2.Route('/cleanup', CleanupHandler),
])

jinjaEnv = jinja2.Environment(
 loader = jinja2.FileSystemLoader('templates'),
 autoescape = True
)
jinjaEnv.globals['uri_for'] = webapp2.uri_for
