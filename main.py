"""A Google appengine application which allows you to download apps from the PMCA store and to install custom apps on your camera"""

import datetime
import hashlib
import jinja2
import json
import os
import webapp2

from google.appengine.ext import blobstore
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers

import config
from pmca import appstore
from pmca import marketclient
from pmca import marketserver
from pmca import spk
from pmca import xpd


class Task(ndb.Model):
 """The Entity used to save task data in the datastore between requests"""
 blob = ndb.BlobKeyProperty(indexed = False)
 app = ndb.StringProperty(indexed = False)
 date = ndb.DateTimeProperty(auto_now_add = True)
 completed = ndb.BooleanProperty(default = False, indexed = False)
 response = ndb.TextProperty()


class Camera(ndb.Model):
 model = ndb.StringProperty(indexed=False)
 apps = ndb.JsonProperty(default={})
 firstDate = ndb.DateTimeProperty(indexed=False, auto_now_add=True)
 lastDate = ndb.DateTimeProperty(indexed=False, auto_now=True)


class Counter(ndb.Model):
 count = ndb.IntegerProperty(indexed=False, default=0)

 @classmethod
 def _getInstance(cls, id):
  return cls.get_by_id(id) or cls(id=id)

 @classmethod
 def getValue(cls, id):
  return cls._getInstance(id).count

 @classmethod
 @ndb.transactional
 def increment(cls, id):
  instance = cls._getInstance(id)
  instance.count += 1
  instance.put()

class CameraModelCounter(Counter):
 pass

class AppInstallCounter(Counter):
 pass

class AppUpdateCounter(Counter):
 pass


def cached(key, func, time=15*60):
 # TODO values > 1MB
 res = memcache.get(key)
 if not res:
  res = func()
  try:
   memcache.add(key, res, time)
  except:
   pass
 return res


class RankedApp(appstore.App):
 def __getattr__(self, name):
  if name == 'rank':
   return self.dict['rank']
  return super(RankedApp, self).__getattr__(name)

class RankedAppStore(appstore.AppStore):
 def _loadApps(self):
  apps = list(super(RankedAppStore, self)._loadApps())
  for dict in apps:
   dict['rank'] = AppInstallCounter.getValue(dict.get('package'))
  return sorted(apps, key=lambda dict: dict['rank'], reverse=True)
 def _createAppInstance(self, dict):
  return RankedApp(self.repo, dict)


class CachedRelease(appstore.Release):
 def _loadAsset(self):
  return cached('app_release_asset_%s_%s_%s' % (self.package, self.version, self.url), super(CachedRelease, self)._loadAsset, 24*3600)

class CachedApp(RankedApp):
 def _loadRelease(self):
  return cached('app_release_%s' % self.package, super(CachedApp, self)._loadRelease)
 def _createReleaseInstance(self, dict):
  return CachedRelease(self.package, dict)

class CachedAppStore(RankedAppStore):
 def _loadApps(self):
  return cached('app_list', lambda: list(super(CachedAppStore, self)._loadApps()))
 def _createAppInstance(self, dict):
  return CachedApp(self.repo, dict)


class AppStore(CachedAppStore):
 def __init__(self):
  repo = appstore.GithubApi(config.githubAppListUser, config.githubAppListRepo, (config.githubClientId, config.githubClientSecret))
  super(AppStore, self).__init__(repo)


def diffApps(oldApps, newApps):
 installedApps = []
 updatedApps = []
 for app, version in newApps.iteritems():
  if oldApps.get(app) != version:
   if app not in oldApps:
    installedApps.append(app)
   updatedApps.append(app)
  oldApps[app] = version
 return oldApps, installedApps, updatedApps

def updateAppStats(data):
 device = data.get('deviceinfo', {})
 apps = dict((app['name'], app['version']) for app in data.get('applications', []) if 'name' in app and 'version' in app)
 if 'name' in device and 'productcode' in device and 'deviceid' in device:
  id = hashlib.sha1('camera_%s_%s_%s' % (device['name'], device['productcode'], device['deviceid'])).hexdigest()
  camera = Camera.get_by_id(id)
  isNewCamera = not camera
  if not camera:
   camera = Camera(id=id)
  camera.model = device['name']
  camera.apps, installed, updated = diffApps(camera.apps, apps)
  camera.put()
  if isNewCamera:
   CameraModelCounter.increment(camera.model)
  for app in installed:
   AppInstallCounter.increment(app)
  for app in updated:
   AppUpdateCounter.increment(app)


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


class AjaxUploadHandler(BaseHandler, blobstore_handlers.BlobstoreUploadHandler):
 """An api to upload apk files"""
 def get(self):
  self.json({'url': blobstore.create_upload_url(self.uri_for('ajaxUpload'))})

 def post(self):
  uploads = self.get_uploads()
  if len(uploads) != 1:
   return self.error(400)
  return self.json({'key': str(uploads[0].key())})


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
  app = AppStore().apps.get(appId)
  if not app:
   return self.error(404)
  self.get({'app': app})


class PluginInstallHandler(BaseHandler):
 """Displays the help text to install the PMCA Downloader plugin"""
 def get(self):
  self.template('plugin/install.html', {
   'text': cached('plugin_install_text', marketclient.getPluginInstallText, 24*3600),
  })


class TaskStartHandler(BaseHandler):
 """Creates a new task sequence and returns its id"""
 def get(self, task = None):
  if task is None:
   task = Task()
  taskId = task.put().id()
  self.json({'id': taskId})

 def getBlob(self, blobKey):
  blob = blobstore.get(blobKey)
  if not blob:
   return self.error(404)
  self.get(Task(blob = blob.key()))

 def getApp(self, appId):
  if not AppStore().apps.get(appId):
   return self.error(404)
  self.get(Task(app = appId))


class TaskViewHandler(BaseHandler):
 """Displays the result of the given task sequence (called over AJAX)"""
 def queryTask(self, taskKey):
  task = ndb.Key(Task, int(taskKey)).get()
  if not task:
   return self.error(404)
  return {
   'completed': task.completed,
   'response': marketserver.parsePostData(task.response) if task.completed else None,
  }

 def getTask(self, taskKey):
  self.json(self.queryTask(taskKey))

 def viewTask(self, taskKey):
  self.template('task/view.html', self.queryTask(taskKey))


class XpdHandler(BaseHandler):
 """Returns the xpd file corresponding to the given task sequence (called by the plugin)"""
 def get(self, taskKey):
  task = ndb.Key(Task, int(taskKey)).get()
  if not task:
   return self.error(404)
  xpdData = marketserver.getXpdResponse(task.key.id(), self.uri_for('portal', _scheme='https'))
  self.output(xpd.constants.mimeType, xpdData)


class PortalHandler(BaseHandler):
 """Saves the data sent by the camera to the datastore and returns the actions to be taken next (called by the camera)"""
 def post(self):
  data = self.request.body
  dataDict = marketserver.parsePostData(data)
  taskKey = int(dataDict.get('session', {}).get('correlationid', 0))
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
  updateAppStats(dataDict)
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
  app = AppStore().apps.get(appId)
  if not app or not app.release:
   return self.error(404)
  apkData = app.release.asset
  self.get(apkData)


class AppsHandler(BaseHandler):
 """Displays apps available on github"""
 def get(self):
  self.template('apps/list.html', {
   'repo': (config.githubAppListUser, config.githubAppListRepo),
   'apps': AppStore().apps,
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
 webapp2.Route('/ajax/upload', AjaxUploadHandler, 'ajaxUpload'),
 webapp2.Route('/ajax/task/start', TaskStartHandler, 'taskStart'),
 webapp2.Route('/ajax/task/start/blob/<blobKey>', TaskStartHandler, 'blobTaskStart', handler_method = 'getBlob'),
 webapp2.Route('/ajax/task/start/app/<appId>', TaskStartHandler, 'appTaskStart', handler_method = 'getApp'),
 webapp2.Route('/ajax/task/get/<taskKey>', TaskViewHandler, 'taskGet', handler_method = 'getTask'),
 webapp2.Route('/ajax/task/view/<taskKey>', TaskViewHandler, 'taskView', handler_method = 'viewTask'),
 webapp2.Route('/camera/xpd/<taskKey>', XpdHandler, 'xpd'),
 webapp2.Route('/camera/portal', PortalHandler, 'portal'),
 webapp2.Route('/download/spk/blob/<blobKey>', SpkHandler, 'blobSpk', handler_method = 'getBlob'),
 webapp2.Route('/download/spk/app/<appId>', SpkHandler, 'appSpk', handler_method = 'getApp'),
 webapp2.Route('/apps', AppsHandler, 'apps'),
 webapp2.Route('/cleanup', CleanupHandler),
])

jinjaEnv = jinja2.Environment(
 loader = jinja2.FileSystemLoader('templates'),
 autoescape = True
)
jinjaEnv.globals['uri_for'] = webapp2.uri_for
jinjaEnv.globals['versionHash'] = hashlib.sha1(os.environ['CURRENT_VERSION_ID']).hexdigest()[:8]
