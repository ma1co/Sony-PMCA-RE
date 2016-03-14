import itertools
import re

def parseDeviceId(id):
 match = re.search('(#|\\\\)vid_([a-f0-9]{4})&pid_([a-f0-9]{4})(&|#|\\\\)', id, re.IGNORECASE)
 return [int(match.group(i), 16) if match else None for i in [2, 3]]

import msc
from msc import MscDriver
import wpd
from wpd import MtpDriver

def listDevices():
 """Lists all mass storage and MTP devices"""
 return itertools.chain(msc.listDevices(), wpd.listDevices())
