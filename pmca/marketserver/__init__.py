"""Provides the server part of the functionality used to download apps over USB"""

import json

from . import constants
from .. import xpd

def parsePostData(data):
 """Parses the data submitted by the camera to the portal url

 Returns:
  {
   'accountinfo': {
    'signinid': 'appstore email address',
    'accountid': 'appstore portal id',
    'registered': '1',
   },
   'applications': [{
    'name': 'application name',
    'version': 'application version',
   }, ...],
   'deviceinfo': {
    'deviceid': 'device id',
    'fwversion': 'firmware version',
    'productcode': 'product code',
    'name': 'camera name',
    'battery': 'battery level',
    'freespace': 'free space',
    'storagetotalsize': 'total space',
   },
   'session': {
    'correlationid': 'correlation id',
   },
   'profileversion': {
    'version': '1',
   },
  }
 """
 return json.loads(data.decode('latin1'))

def getXpdResponse(correlation, url):
 """Creates an xpd file which points the camera to the supplied portal url"""
 return xpd.dump({
  'TCD': url,
  'TKN': correlation,
  'CIC': xpd.calculateChecksum(url.encode('latin1'))
 })

def getJsonInstallResponse(appName, spkUrl):
 """Creates the response that has to be returned by the portal url to install the given app"""
 return json.dumps({"actions": [{
  "command": "dlandinstall",
  "args": spkUrl,
  "attrs": [{
   "attrname": "appname",
   "attrvalue": appName,
  }],
 }]}).encode('latin1')

def getJsonResponse():
 """Creates the response that has to be returned by the portal url if no more actions have to be taken"""
 return json.dumps({"actions": []}).encode('latin1')
