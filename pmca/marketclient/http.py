""" Some methods to make HTTP requests"""

import urllib
import urllib2
from cookielib import CookieJar

def post(url, data, headers={}, cookies={}, auth=None, returnHeaders=False):
 qs = urlencode(data)
 return request(url, qs, headers, cookies, auth, returnHeaders)

def get(url, data={}, headers={}, cookies={}, auth=None, returnHeaders=False):
 qs = urlencode(data)
 if qs:
  url += '?' + qs
 return request(url, None, headers, cookies, auth, returnHeaders)

def request(url, data=None, headers={}, cookies={}, auth=None, returnHeaders=False):
 cookieHeader = cookieencode(cookies)
 if cookieHeader:
  headers['Cookie'] = cookieHeader
 request = urllib2.Request(url, data, headers)
 manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
 if auth:
  manager.add_password(None, request.get_full_url(), auth[0], auth[1])
 opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(manager), urllib2.HTTPDigestAuthHandler(manager))
 response = opener.open(request)
 if returnHeaders:
  cj = CookieJar()
  cj.extract_cookies(response, request)
  return response.read(), response.info().headers, dict((c.name, c.value) for c in cj)
 else:
  return response.read()

def urlencode(data):
 return urllib.urlencode(data)

def cookieencode(data):
 return '; '.join(urllib.quote(k) + '=' + urllib.quote(v) for (k, v) in data.iteritems())
