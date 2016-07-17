import json
import os
import sys
import time

from .. import installer
from ..marketserver.server import *
from ..usb import *
from ..usb.driver import *
from ..usb.sony import *

scriptRoot = getattr(sys, '_MEIPASS', os.path.dirname(__file__) + '/../..')


def printStatus(status):
 """Print progress"""
 print '%s %d%%' % (status.message, status.percent)


def switchToAppInstaller(dev):
 """Switches a camera in MTP mode to app installation mode"""
 print 'Switching to app install mode'
 SonyExtCmdCamera(dev).switchToAppInstaller()


defaultCertFile = scriptRoot + '/certs/localtest.me.pem'
def installApp(dev, host=None, apkFile=None, outFile=None, certFile=defaultCertFile):
 """Installs an app on the specified device."""
 apk = (os.path.basename(apkFile.name), apkFile.read()) if apkFile else None

 if host:
  server = RemoteMarketServer(host, apk)
 else:
  server = LocalMarketServer(certFile, apk)

 print ('Uploading apk' if apk else 'Starting task') if host else 'Starting server'
 server.run()
 xpdData = server.getXpd()

 print 'Starting communication'
 # Point the camera to the web api
 result = installer.install(dev, xpdData, printStatus)
 if result.code != 0:
  raise Exception('Communication error %d: %s' % (result.code, result.message))

 print 'Downloading result' if host else 'Stopping server'
 result = server.getResult()
 server.shutdown()

 print 'Task completed successfully'

 if outFile:
  print 'Writing to output file'
  json.dump(result, outFile, indent=2)

 return result


def importDriver(driverName=None):
 """Imports the usb driver. Use in a with statement"""
 if not driverName:
  driverName = 'windows' if os.name == 'nt' else 'libusb'

 # Import the specified driver
 if driverName == 'libusb':
  print 'Using libusb'
  from ..usb.driver import libusb as driver
 elif driverName == 'windows':
  print 'Using Windows drivers'
  from ..usb.driver import windows as driver
 else:
  raise Exception('Unknown driver')

 return driver.Context()


def listDevices(driver):
 """List all Sony usb devices"""
 print 'Looking for Sony devices'
 for device in driver.listDevices(SONY_ID_VENDOR):
  if device.type == USB_CLASS_MSC:
   print '\nQuerying mass storage device'
   # Get device info
   drv = driver.MscDriver(device)
   info = MscDevice(drv).getDeviceInfo()

   if isSonyMscCamera(info):
    print '%s %s is a camera in mass storage mode' % (info.manufacturer, info.model)
    yield SonyMscCamera(drv)

  elif device.type == USB_CLASS_PTP:
   print '\nQuerying MTP device'
   # Get device info
   drv = driver.MtpDriver(device)
   info = MtpDevice(drv).getDeviceInfo()

   if isSonyMtpCamera(info):
    print '%s %s is a camera in MTP mode' % (info.manufacturer, info.model)
    yield SonyMtpCamera(drv)
   elif isSonyMtpAppInstaller(info):
    print '%s %s is a camera in app install mode' % (info.manufacturer, info.model)
    yield SonyMtpAppInstaller(drv)
  print ''


def getDevice(driver):
 """Check for exactly one Sony usb device"""
 devices = list(listDevices(driver))
 if not devices:
  print 'No devices found. Ensure your camera is connected.'
 elif len(devices) != 1:
  print 'Too many devices found. Only one camera is supported'
 else:
  return devices[0]


def infoCommand(host=None, driverName=None):
 """Display information about the camera connected via usb"""
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if isinstance(device, SonyMtpAppInstaller):
    info = installApp(device, host)
    print ''
    props = [
     ('Model', info['deviceinfo']['name']),
     ('Product code', info['deviceinfo']['productcode']),
     ('Serial number', info['deviceinfo']['deviceid']),
     ('Firmware version', info['deviceinfo']['fwversion']),
    ]
   else:
    info = SonyExtCmdCamera(device).getCameraInfo()
    firmware = SonyUpdaterCamera(device).getFirmwareVersion()
    props = [
     ('Model', info.modelName),
     ('Product code', info.modelCode),
     ('Serial number', info.serial),
     ('Firmware version', firmware),
    ]
   for k, v in props:
    print '%-20s%s' % (k + ': ', v)


def installCommand(host=None, driverName=None, apkFile=None, outFile=None):
 """Install the given apk on the camera"""
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if not isinstance(device, SonyMtpAppInstaller):
    switchToAppInstaller(device)

    print 'Waiting for camera to switch...'
    for i in xrange(10):
     time.sleep(.5)
     devices = list(listDevices(driver))
     if len(devices) == 1 and isinstance(devices[0], SonyMtpAppInstaller):
      device = devices[0]
      break
     elif devices:
      raise Exception('Unexpected device')
    else:
     raise Exception('Timeout')

   installApp(device, host, apkFile, outFile)
