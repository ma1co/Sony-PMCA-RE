"""Some methods to make HTTP requests"""

from collections import namedtuple

try:
 from urllib.parse import *
 from urllib.request import *
except ImportError:
 # Python 2
 from urllib import *
 from urllib2 import *
 from urlparse import *

HttpResponse = namedtuple('HttpResponse', 'url, data, raw_data, headers')

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
 headers = dict(response.headers)
 raw_contents = response.read()
 contents = raw_contents.decode(headers.get('charset', 'latin1'))
 return HttpResponse(urlparse(response.geturl()), contents, raw_contents, headers)
