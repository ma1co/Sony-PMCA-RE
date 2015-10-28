import requests

class WebApi:
 """A simple interface for the appengine website"""
 def __init__(self, baseUrl):
  self.base = baseUrl

 def uploadBlob(self, data, name='app.apk'):
  """Uploads a blob, returns its key"""
  url = requests.get(self.base + '/ajax/upload').json()['url']
  return requests.post(url, files={'file': (name, data)}).json()['key']

 def startTask(self, urlSuffix=''):
  """Starts a task sequence and returns its id"""
  return str(requests.get(self.base + '/ajax/task/start' + urlSuffix).json()['id'])

 def startBlobTask(self, key):
  """Starts the installation task of a previously uploaded apk blob"""
  return self.startTask('/blob/' + key)

 def getXpd(self, task):
  """Downloads the xpd file for a task"""
  return requests.get(self.base + '/camera/xpd/' + task).text.encode('ascii','ignore')

 def getTask(self, task):
  """Returns the task result"""
  return requests.get(self.base + '/ajax/task/get/' + task).json()
