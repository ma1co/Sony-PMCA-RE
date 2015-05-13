"""Provides a client to download apps from the PMCA store"""

import json
import re

import constants
import http
from .. import xpd

def download(portalid, deviceid, appid):
 """Downloads an app from the PMCA store

 Returns:
  The contents of the spk file
 """
 xpdData = downloadXpd(portalid, deviceid, appid)
 name, url = parseXpd(xpdData)
 return name, downloadSpk(url)

def login(email, password):
 """Tries to authenticate the specified user

 Returns:
  The portalid string in case of success or None otherwise
 """
 response, headers, cookies = http.post(constants.loginUrl, data = {
  'j_username': email,
  'j_password': password,
  'returnURL': constants.baseUrl + '/forward.php',
 }, returnHeaders = True)
 return cookies['portalid'] if 'portalid' in cookies else None

def getDevices(portalid):
 """Fetches the list of devices for the current user

 Returns:
  [{
   'deviceid': 'device id',
   'name': 'camera name',
   'serial': 'serial number',
  }, ...]
 """
 data = json.loads(http.get(constants.baseUrl + '/dialog.php?case=mycamera', cookies = {
  'portalid': portalid,
 }))
 contents = data['mycamera']['contents']
 r = re.compile('<div class="camera-manage-box" id="(?P<deviceid>\d*?)">.*?<td class = "w104 h20">(?P<name>.*?)</td>.*?<span class="sirial-hint">Serial:(?P<serial>.*?)</span>', re.DOTALL)
 return [m.groupdict() for m in r.finditer(contents)]

def getPluginInstallText():
 """Fetches the English help text for installing the PMCA Downloader plugin"""
 data = json.loads(http.get(constants.baseUrl + '/dialog.php?case=installingPlugin', cookies = {
  'localeid': constants.localeUs,
 }))
 contents = data['installingPlugin']['contents']
 r = re.compile('<div id="notinstallpopup".*?>(.*?)</div>', re.DOTALL)
 return r.search(contents).group(1)

def getApps(deviceid):
 """Fetches the list of apps compatible with the given device

 Note: The US locale is used.
 This may return apps that aren't available in the region connected to your account.
 We want to get Dollar prices however.

 Returns:
  [{
   'id': 'app id',
   'name': 'app name',
   'img': 'image url',
   'status': '$1.00 / Install / Installed',
  }, ...]
 """
 data = http.get(constants.baseUrl + '/wifiall.php', headers = {
  'User-Agent': constants.cameraUserAgent,
 }, cookies = {
  'deviceid': deviceid,
  'localeid': constants.localeUs,
 })
 r = re.compile('<td class="app-name">(?P<name>.*?)</td>.*?<a href="\./wifidetail\.php\?EID=(?P<id>.*?)&.*?<img src="(?P<img>.*?)".*?<td class="app-status">(?P<status>.*?)</td>', re.DOTALL)
 apps = [m.groupdict() for m in r.finditer(data)]
 for app in apps:
  app['name'] = app['name'].replace('<br />', ' ')
 return apps

def downloadXpd(portalid, deviceid, appid):
 """Fetches the xpd file for the given app

 Returns:
  The contents of the xpd file
 """
 return http.get(constants.baseUrl + '/wifixpwd.php', data = {
  'EID': appid,
 }, headers = {
  'User-Agent': constants.cameraUserAgent,
 }, cookies = {
  'portalid': portalid,
  'deviceid': deviceid,
 })

def parseXpd(data):
 """Parses an xpd file

 Returns:
  ('file name', 'spk url')
 """
 config = xpd.parse(data)
 return config['FNAME'], config['OUS']

def downloadSpk(url):
 """Downloads an spk file

 Returns:
  The contents of the spk file
 """
 return http.get(url, auth = (constants.downloadAuthUser, constants.downloadAuthPassword))
