"""Some methods to make HTTP requests"""

import mimetools
import urllib
import urllib2
from cookielib import CookieJar
from collections import namedtuple

HttpResponse = namedtuple('HttpResponse', 'data, headers, cookies')

def postForm(url, data, headers={}, cookies={}, auth=None):
 return post(url, urllib.urlencode(data), headers, cookies, auth)

def postFile(url, fileName, fileData, fieldName='', headers={}, cookies={}, auth=None):
 boundary = mimetools.choose_boundary()
 headers['Content-type'] = 'multipart/form-data; boundary=%s' % boundary
 data = '\r\n'.join([
  '--%s' % boundary,
  'Content-Disposition: form-data; name="%s"; filename="%s"' % (fieldName, fileName),
  '',
  fileData,
  '--%s--' % boundary,
  '',
 ])
 return request(url, data, headers, cookies, auth)

def get(url, data={}, headers={}, cookies={}, auth=None):
 if data:
  url += '?' + urllib.urlencode(data)
 return request(url, None, headers, cookies, auth)

def post(url, data, headers={}, cookies={}, auth=None):
 return request(url, data, headers, cookies, auth)

def request(url, data=None, headers={}, cookies={}, auth=None):
 if cookies:
  headers['Cookie'] = '; '.join(urllib.quote(k) + '=' + urllib.quote(v) for (k, v) in cookies.iteritems())
 request = urllib2.Request(url.encode('utf8'), data, headers)
 manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
 if auth:
  manager.add_password(None, request.get_full_url(), auth[0], auth[1])
 opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(manager), urllib2.HTTPDigestAuthHandler(manager))
 response = opener.open(request)
 cj = CookieJar()
 cj.extract_cookies(response, request)
 return HttpResponse(response.read(), response.info().headers, dict((c.name, c.value) for c in cj))
