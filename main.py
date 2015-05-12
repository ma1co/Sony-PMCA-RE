import jinja2
import json
import re
import webapp2

from google.appengine.ext import blobstore
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers

from pmca import marketclient
from pmca import marketserver
from pmca import spk
from pmca import xpd


class Task(ndb.Model):
 blob = ndb.BlobKeyProperty()
 date = ndb.DateTimeProperty(auto_now_add = True)
 completed = ndb.BooleanProperty(default = False)
 response = ndb.TextProperty()


class BaseHandler(webapp2.RequestHandler):
 def json(self, data):
  self.output('application/json', json.dumps(data))

 def template(self, name, data = {}):
  self.response.write(jinjaEnv.get_template(name).render(data))

 def output(self, mimeType, data, filename = None):
  self.response.content_type = mimeType
  if filename:
   self.response.headers['Content-Disposition'] = 'attachment;filename="%s"' % filename
  self.response.write(data)


class HomeHandler(BaseHandler):
 def get(self):
  self.template('home.html')


class ApkUploadHandler(BaseHandler, blobstore_handlers.BlobstoreUploadHandler):
 def get(self):
  self.template('apk/upload.html', {
   'uploadUrl': blobstore.create_upload_url(self.uri_for('apkUpload')),
  })

 def post(self):
  uploads = self.get_uploads()
  if len(uploads) == 1:
   return self.redirect_to('apkPlugin', blobKey = uploads[0].key())
  self.get()


class PluginHandler(BaseHandler):
 def get(self, blobKey=None):
  blob = None
  if blobKey:
   blob = blobstore.get(blobKey)
   if not blob:
    return self.error(404)
  self.template('plugin/start.html', {
   'blob': blob,
  })


class PluginInstallHandler(BaseHandler):
 def get(self):
  self.template('plugin/install.html', {
   'text': marketclient.getPluginInstallText(),
  })


class TaskStartHandler(BaseHandler):
 def get(self, blobKey=None):
  if blobKey:
   blob = blobstore.get(blobKey)
   if not blob:
    return self.error(404)
   blobKey = blob.key()
  taskId = Task(blob = blobKey).put().id()
  self.json({'id': taskId})


class TaskViewHandler(BaseHandler):
 def get(self, taskKey):
  task = ndb.Key(Task, int(taskKey)).get()
  if not task:
   return self.error(404)
  self.template('task/view.html', {
   'completed': task.completed,
   'response': marketserver.parsePostData(task.response) if task.completed else None,
  })


class XpdHandler(BaseHandler):
 def get(self, taskKey):
  task = ndb.Key(Task, int(taskKey)).get()
  if not task:
   return self.error(404)
  xpdData = marketserver.getXpdResponse(task.key.id(), self.uri_for('portal', _full = True))
  self.output(xpd.constants.mimeType, xpdData)


class PortalHandler(BaseHandler):
 def post(self):
  data = self.request.body
  taskKey = int(marketserver.parsePostData(data)['session']['correlationid'])
  task = ndb.Key(Task, taskKey).get()
  if not task:
   return self.error(404)
  if not task.completed and task.blob:
   response = marketserver.getJsonInstallResponse('App', self.uri_for('spk', blobKey = task.blob, _full = True))
  else:
   response = marketserver.getJsonResponse()
  task.completed = True
  task.response = data
  task.put()
  self.output(marketserver.constants.jsonMimeType, response)


class SpkHandler(BaseHandler):
 def get(self, blobKey):
  blob = blobstore.get(blobKey)
  if not blob:
   return self.error(404)
  with blob.open() as f:
   apkData = f.read()
  spkData = spk.dump(apkData)
  self.output(spk.constants.mimeType, spkData, "app%s" % spk.constants.extension)


class MarketLoginHandler(BaseHandler):
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
 def get(self, portalid):
  self.template('market/devices.html', {
   'devices': marketclient.getDevices(portalid),
   'portalid': portalid,
  })


class MarketAppsHandler(BaseHandler):
 def get(self, portalid, deviceid):
  self.template('market/apps.html', {
   'apps': [app for app in marketclient.getApps(deviceid) if not app['status'].startswith('$')],
   'portalid': portalid,
   'deviceid': deviceid,
  })


class MarketDownloadHandler(BaseHandler):
 def get(self, portalid, deviceid, appid):
  spkName, spkData = marketclient.download(portalid, deviceid, appid)
  apkData = spk.parse(spkData)
  apkName = re.sub('(%s)?$' % re.escape(spk.constants.extension), '.apk', spkName)
  self.output('application/vnd.android.package-archive', apkData, apkName)


app = webapp2.WSGIApplication([
 webapp2.Route('/', HomeHandler, 'home'),
 webapp2.Route('/upload', ApkUploadHandler, 'apkUpload'),
 webapp2.Route('/plugin', PluginHandler, 'plugin'),
 webapp2.Route('/plugin/blob/<blobKey>', PluginHandler, 'apkPlugin'),
 webapp2.Route('/plugin/install', PluginInstallHandler, 'installPlugin'),
 webapp2.Route('/ajax/task/start', TaskStartHandler, 'taskStart'),
 webapp2.Route('/ajax/task/start/<blobKey>', TaskStartHandler, 'apkTaskStart'),
 webapp2.Route('/ajax/task/view/<taskKey>', TaskViewHandler, 'taskView'),
 webapp2.Route('/camera/xpd/<taskKey>', XpdHandler, 'xpd'),
 webapp2.Route('/camera/portal', PortalHandler, 'portal'),
 webapp2.Route('/camera/spk/<blobKey>', SpkHandler, 'spk'),
 webapp2.Route('/market', MarketLoginHandler, 'marketLogin'),
 webapp2.Route('/market/<portalid>', MarketDevicesHandler, 'marketDevices'),
 webapp2.Route('/market/<portalid>/<deviceid>', MarketAppsHandler, 'marketApps'),
 webapp2.Route('/market/<portalid>/<deviceid>/<appid>', MarketDownloadHandler, 'marketDownload'),
])

jinjaEnv = jinja2.Environment(
 loader = jinja2.FileSystemLoader('templates'),
 autoescape = True
)
jinjaEnv.globals['uri_for'] = webapp2.uri_for
