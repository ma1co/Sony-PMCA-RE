import json

import constants
from .. import xpd

def parsePostData(data):
 return json.loads(data)

def getXpdResponse(correlation, url):
 return xpd.dump({
  'TCD': url,
  'TKN': correlation,
  'CIC': xpd.calculateChecksum(url)
 })

def getJsonInstallResponse(appName, spkUrl):
 return json.dumps({"actions": [{
  "command": "dlandinstall",
  "args": spkUrl,
  "attrs": [{
   "attrname": "appname",
   "attrvalue": appName,
  }],
 }]})

def getJsonResponse():
 return json.dumps({"actions": []})
