import json
import re

import constants
import http
from .. import xpd

def download(portalid, deviceid, appid):
 xpdData = downloadXpd(portalid, deviceid, appid)
 name, url = parseXpd(xpdData)
 return name, downloadSpk(url)

def login(email, password):
 response, headers, cookies = http.post(constants.loginUrl, data = {
  'j_username': email,
  'j_password': password,
  'returnURL': constants.baseUrl + '/forward.php',
 }, returnHeaders = True)
 return cookies['portalid'] if 'portalid' in cookies else None

def getDevices(portalid):
 data = json.loads(http.get(constants.baseUrl + '/dialog.php?case=mycamera', cookies = {
  'portalid': portalid,
 }))
 contents = data['mycamera']['contents']
 r = re.compile('<div class="camera-manage-box" id="(?P<deviceid>\d*?)">.*?<td class = "w104 h20">(?P<name>.*?)</td>.*?<span class="sirial-hint">Serial:(?P<serial>.*?)</span>', re.DOTALL)
 return [m.groupdict() for m in r.finditer(contents)]

def getPluginInstallText():
 data = json.loads(http.get(constants.baseUrl + '/dialog.php?case=installingPlugin', cookies = {
  'localeid': constants.localeUs,
 }))
 contents = data['installingPlugin']['contents']
 r = re.compile('<div id="notinstallpopup".*?>(.*?)</div>', re.DOTALL)
 return r.search(contents).group(1)

def getApps(deviceid):
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
 return http.get(constants.baseUrl + '/wifixpwd.php', data = {
  'EID': appid,
 }, headers = {
  'User-Agent': constants.cameraUserAgent,
 }, cookies = {
  'portalid': portalid,
  'deviceid': deviceid,
 })

def parseXpd(data):
 config = xpd.parse(data)
 return config['FNAME'], config['OUS']

def downloadSpk(url):
 return http.get(url, auth = (constants.downloadAuthUser, constants.downloadAuthPassword))
