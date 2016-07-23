from getpass import getpass
import os
import re

from .. import marketclient
from .. import spk

def marketCommand(token=None):
 if not token:
  print 'Please enter your Sony Entertainment Network credentials\n'
  email = raw_input('Email: ')
  password = getpass('Password: ')
  token = marketclient.login(email, password)
  if token:
   print 'Login successful. Your auth token (use with the -t option):\n%s\n' % token
  else:
   print 'Login failed'
   return

 devices = marketclient.getDevices(token)
 print '%d devices found\n' % len(devices)

 apps = []
 for device in devices:
  print '%s (%s)' % (device.name, device.serial)
  for app in marketclient.getApps(device.name):
   if not app.price:
    apps.append((device.deviceid, app.id))
    print ' [%2d] %s' % (len(apps), app.name)
  print ''

 if apps:
  while True:
   i = int(raw_input('Enter number of app to download (0 to exit): '))
   if i == 0:
    break
   app = apps[i - 1]
   print 'Downloading app %s' % app[1]
   spkName, spkData = marketclient.download(token, app[0], app[1])
   fn = re.sub('(%s)?$' % re.escape(spk.constants.extension), '.apk', spkName)
   data = spk.parse(spkData)

   if os.path.exists(fn):
    print 'File %s exists already' % fn
   else:
    with open(fn, 'wb') as f:
     f.write(data)
    print 'App written to %s' % fn
   print ''
