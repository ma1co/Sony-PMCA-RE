import hashlib
import hmac
from ConfigParser import ConfigParser
from StringIO import StringIO

import constants

def parse(data):
 config = ConfigParser()
 config.optionxform = str
 config.readfp(StringIO(data))
 return dict(config.items(constants.sectionName))

def dump(items):
 config = ConfigParser()
 config.optionxform = str
 config.add_section(constants.sectionName)
 for k, v in items.iteritems():
  config.set(constants.sectionName, k, v)
 f = StringIO()
 config.write(f)
 return f.getvalue()

def calculateChecksum(data):
 return hmac.new(constants.cicKey, data, hashlib.sha256).hexdigest()
