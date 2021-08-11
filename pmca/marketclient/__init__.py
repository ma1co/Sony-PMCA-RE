"""Provides a client to download apps from the PMCA store"""

from collections import namedtuple
import json
import posixpath
import re

from . import constants
from ..util import http
from .. import xpd

MarketDevice = namedtuple('MarketDevice', 'deviceid, name, serial')
MarketApp = namedtuple('MarketApp', 'id, name, img, price, date')

def download(portalid, deviceid, appid):
 """Downloads an app from the PMCA store

 Returns:
  ('file name', 'spk data')
 """
 xpdData = downloadXpd(portalid, deviceid, appid)
 name, url = parseXpd(xpdData)
 return downloadSpk(url)

def getDevices(portalid):
 """Fetches the list of devices for the current user"""
 data = json.loads(http.get(constants.baseUrl + '/dialog.php?case=mycamera', cookies = {
  'portalid': portalid,
  'localeid': constants.localeUs,
 }).data)
 contents = data['mycamera']['contents']
 r = re.compile('<div class="camera-manage-box" id="(?P<deviceid>\d*?)">.*?<td class = "w104 h20">(?P<name>.*?)</td>.*?<span class="sirial-hint">Serial:(?P<serial>.*?)</span>', re.DOTALL)
 return [MarketDevice(**m.groupdict()) for m in r.finditer(contents)]

def getApps(devicename=None):
 """Fetches the list of apps compatible with the given device"""
 data = json.loads(http.get(constants.baseUrl + '/api/api_all_contents.php', data = {
  'setname': devicename or '',
 }, headers = {
  'X-Requested-With': 'XMLHttpRequest',
 }, cookies = {
  'localeid': constants.localeUs,
 }).data)
 for app in data['contents']:
  yield MarketApp(app['app_id'], re.sub('\s+', ' ', app['app_name']), app['appimg_url'], None if app['app_price'] == 'Free' else app['app_price'], int(app['regist_date']))

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
  'localeid': constants.localeUs,
 }).raw_data

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
  ('file name', 'spk data')
 """
 response = http.get(url, auth = (constants.downloadAuthUser, constants.downloadAuthPassword))
 return posixpath.basename(response.url.path), response.raw_data
