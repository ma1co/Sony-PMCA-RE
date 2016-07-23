"""Methods for reading and writing xpd files"""

from Crypto.Hash import HMAC, SHA256
from ConfigParser import ConfigParser
from StringIO import StringIO

import constants

def parse(data):
 """Parses an xpd file

 Returns:
  A dict containing the properties
 """
 config = ConfigParser()
 config.optionxform = str
 config.readfp(StringIO(data))
 return dict(config.items(constants.sectionName))

def dump(items):
 """Builds an xpd file"""
 config = ConfigParser()
 config.optionxform = str
 config.add_section(constants.sectionName)
 for k, v in items.iteritems():
  config.set(constants.sectionName, k, v)
 f = StringIO()
 config.write(f)
 return f.getvalue()

def calculateChecksum(data):
 """The function used to calculate CIC checksums for xpd files"""
 return HMAC.new(constants.cicKey, data, SHA256).hexdigest()
