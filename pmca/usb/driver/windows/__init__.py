import itertools
import re

def parseDeviceId(id):
 match = re.search('(#|\\\\)vid_([a-f0-9]{4})&pid_([a-f0-9]{4})(&|#|\\\\)', id, re.IGNORECASE)
 return [int(match.group(i), 16) if match else None for i in [2, 3]]

import msc
from msc import MscDriver
import wpd
from wpd import MtpDriver

def listDevices(vendor=None):
 """Lists all mass storage and MTP devices"""
 return (dev for dev in itertools.chain(msc.listDevices(), wpd.listDevices()) if dev.idVendor == vendor)
