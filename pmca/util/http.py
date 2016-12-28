"""Some methods to make HTTP requests"""

from collections import namedtuple
import random
import string

try:
 from urllib.parse import *
 from urllib.request import *
 from http.cookiejar import *
except ImportError:
 # Python 2
 from urllib import *
 from urllib2 import *
 from cookielib import *
 from urlparse import *

HttpResponse = namedtuple('HttpResponse', 'url, data, raw_data, headers, cookies')

def postForm(url, data, headers={}, cookies={}, auth=None):
 return post(url, urlencode(data).encode('latin1'), headers, cookies, auth)

def postFile(url, fileName, fileData, fieldName='', headers={}, cookies={}, auth=None):
 boundary = ''.join(random.choice('-_' + string.digits + string.ascii_letters) for _ in range(40))
 headers['Content-type'] = 'multipart/form-data; boundary=%s' % boundary
 data = b'\r\n'.join([
  b'--' + boundary.encode('latin1'),
  b'Content-Disposition: form-data; name="' + fieldName.encode('latin1') + b'"; filename="' + fileName.encode('latin1') + b'"',
  b'',
  fileData,
  b'--' + boundary.encode('latin1') + b'--',
  b'',
 ])
 return request(url, data, headers, cookies, auth)

def get(url, data={}, headers={}, cookies={}, auth=None):
 if data:
  url += '?' + urlencode(data)
 return request(url, None, headers, cookies, auth)

def post(url, data, headers={}, cookies={}, auth=None):
 return request(url, data, headers, cookies, auth)

def request(url, data=None, headers={}, cookies={}, auth=None):
 if cookies:
  headers['Cookie'] = '; '.join(quote(k) + '=' + quote(v) for (k, v) in cookies.items())
 request = Request(str(url), data, headers)
 manager = HTTPPasswordMgrWithDefaultRealm()
 if auth:
  manager.add_password(None, request.get_full_url(), auth[0], auth[1])
 handlers = [HTTPBasicAuthHandler(manager), HTTPDigestAuthHandler(manager)]
 try:
  import certifi, ssl
  handlers.append(HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())))
 except:
  # App engine
  pass
 response = build_opener(*handlers).open(request)
 cj = CookieJar()
 cj.extract_cookies(response, request)
 headers = dict(response.headers)
 raw_contents = response.read()
 contents = raw_contents.decode(headers.get('charset', 'latin1'))
 return HttpResponse(urlparse(response.geturl()), contents, raw_contents, headers, dict((c.name, c.value) for c in cj))
