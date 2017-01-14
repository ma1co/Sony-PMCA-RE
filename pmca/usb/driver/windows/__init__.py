import re

def parseDeviceId(id):
 match = re.search('(#|\\\\)vid_([a-f0-9]{4})&pid_([a-f0-9]{4})(&|#|\\\\)', id, re.IGNORECASE)
 return [int(match.group(i), 16) if match else None for i in [2, 3]]
