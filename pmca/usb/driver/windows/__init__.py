import comtypes
import itertools
import re
import sys

def parseDeviceId(id):
 match = re.search('(#|\\\\)vid_([a-f0-9]{4})&pid_([a-f0-9]{4})(&|#|\\\\)', id, re.IGNORECASE)
 return [int(match.group(i), 16) if match else None for i in [2, 3]]

from . import msc
from .msc import MscDriver
from . import wpd
from .wpd import MtpDriver

class Context(object):
 """Use this in a with statement when using the driver"""
 def __enter__(self):
  comtypes.CoInitialize()
  return sys.modules[__name__]

 def __exit__(self, type, value, traceback):
  comtypes.CoUninitialize()

def listDevices(vendor=None):
 """Lists all mass storage and MTP devices"""
 return (dev for dev in itertools.chain(msc.listDevices(), wpd.listDevices()) if dev.idVendor == vendor)
