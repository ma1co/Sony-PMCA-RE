from __future__ import print_function
import json
import os
import sys
import time

if sys.version_info < (3,):
 # Python 2
 input = raw_input

import config
from .. import appstore
from .. import firmware
from .. import installer
from ..marketserver.server import *
from ..usb import *
from ..usb.driver import *
from ..usb.sony import *

scriptRoot = getattr(sys, '_MEIPASS', os.path.dirname(__file__) + '/../..')


def printStatus(status):
 """Print progress"""
 print('%s %d%%' % (status.message, status.percent))


def switchToAppInstaller(dev):
 """Switches a camera in MTP mode to app installation mode"""
 print('Switching to app install mode')
 SonyExtCmdCamera(dev).switchToAppInstaller()


defaultAppStoreRepo = appstore.GithubApi(config.githubAppListUser, config.githubAppListRepo)
defaultCertFile = scriptRoot + '/certs/localtest.me.pem'
def createMarketServer(host=None, repo=defaultAppStoreRepo, certFile=defaultCertFile):
 if host:
  print('Using remote server %s' % host)
  return RemoteMarketServer(host)
 else:
  print('Using local server')
  return LocalMarketServer(repo, certFile)


def listApps(host=None):
 print('Loading app list')
 server = createMarketServer(host)
 apps = list(server.listApps().values())
 print('Found %d apps' % len(apps))
 return apps


def installApp(dev, host=None, apkFile=None, appPackage=None, outFile=None):
 """Installs an app on the specified device."""
 with ServerContext(createMarketServer(host)) as server:
  if apkFile:
   if isinstance(server, RemoteMarketServer):
    print('Uploading apk')
   server.setApk(os.path.basename(apkFile.name), apkFile.read())
  elif appPackage:
   if isinstance(server, LocalMarketServer):
    print('Downloading apk')
   server.setApp(appPackage)

  print('Starting task')
  xpdData = server.getXpd()

  print('Starting communication')
  # Point the camera to the web api
  result = installer.install(dev, server.host, server.port, xpdData, printStatus)
  if result.code != 0:
   raise Exception('Communication error %d: %s' % (result.code, result.message))

  if isinstance(server, RemoteMarketServer):
   print('Downloading result')
  result = server.getResult()

  print('Task completed successfully')

  if outFile:
   print('Writing to output file')
   json.dump(result, outFile, indent=2)

  return result


def importDriver(driverName=None):
 """Imports the usb driver. Use in a with statement"""
 if not driverName:
  driverName = 'windows' if os.name == 'nt' else 'libusb'

 # Import the specified driver
 if driverName == 'libusb':
  print('Using libusb')
  from ..usb.driver import libusb as driver
 elif driverName == 'windows':
  print('Using Windows drivers')
  from ..usb.driver import windows as driver
 else:
  raise Exception('Unknown driver')

 return driver.Context()


def listDevices(driver):
 """List all Sony usb devices"""
 print('Looking for Sony devices')
 for device in driver.listDevices(SONY_ID_VENDOR):
  if device.type == USB_CLASS_MSC:
   print('\nQuerying mass storage device')
   # Get device info
   drv = driver.MscDriver(device)
   info = MscDevice(drv).getDeviceInfo()

   if isSonyMscCamera(info):
    print('%s %s is a camera in mass storage mode' % (info.manufacturer, info.model))
    yield SonyMscCamera(drv)

  elif device.type == USB_CLASS_PTP:
   print('\nQuerying MTP device')
   # Get device info
   drv = driver.MtpDriver(device)
   info = MtpDevice(drv).getDeviceInfo()

   if isSonyMtpCamera(info):
    print('%s %s is a camera in MTP mode' % (info.manufacturer, info.model))
    yield SonyMtpCamera(drv)
   elif isSonyMtpAppInstaller(info):
    print('%s %s is a camera in app install mode' % (info.manufacturer, info.model))
    yield SonyMtpAppInstaller(drv)
  print('')


def getDevice(driver):
 """Check for exactly one Sony usb device"""
 devices = list(listDevices(driver))
 if not devices:
  print('No devices found. Ensure your camera is connected.')
 elif len(devices) != 1:
  print('Too many devices found. Only one camera is supported')
 else:
  return devices[0]


def infoCommand(host=None, driverName=None):
 """Display information about the camera connected via usb"""
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if isinstance(device, SonyMtpAppInstaller):
    info = installApp(device, host)
    print('')
    props = [
     ('Model', info['deviceinfo']['name']),
     ('Product code', info['deviceinfo']['productcode']),
     ('Serial number', info['deviceinfo']['deviceid']),
     ('Firmware version', info['deviceinfo']['fwversion']),
    ]
   else:
    info = SonyExtCmdCamera(device).getCameraInfo()
    firmwareOld, firmwareNew = SonyUpdaterCamera(device).getFirmwareVersion()
    props = [
     ('Model', info.modelName),
     ('Product code', info.modelCode),
     ('Serial number', info.serial),
     ('Firmware version', firmwareOld),
    ]
   for k, v in props:
    print('%-20s%s' % (k + ': ', v))


def installCommand(host=None, driverName=None, apkFile=None, appPackage=None, outFile=None):
 """Install the given apk on the camera"""
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if not isinstance(device, SonyMtpAppInstaller):
    switchToAppInstaller(device)

    print('Waiting for camera to switch...')
    for i in range(10):
     time.sleep(.5)
     devices = list(listDevices(driver))
     if len(devices) == 1 and isinstance(devices[0], SonyMtpAppInstaller):
      device = devices[0]
      break
     elif devices:
      raise Exception('Unexpected device')
    else:
     raise Exception('Timeout')

   installApp(device, host, apkFile, appPackage, outFile)


def appSelectionCommand(host=None):
 apps = listApps(host)
 for i, app in enumerate(apps):
  print(' [%2d] %s' % (i+1, app.package))
 i = int(input('Enter number of app to install (0 to abort): '))
 if i != 0:
  pkg = apps[i - 1].package
  print('')
  print('Installing %s' % pkg)
  return pkg


def firmwareUpdateCommand(file, driverName=None):
 offset, size = firmware.readDat(file)

 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if isinstance(device, SonyMtpAppInstaller):
    print('Error: Cannot use camera in app install mode. Please restart the device.')
    return

   dev = SonyUpdaterCamera(device)

   print('Initializing firmware update')
   dev.init()
   file.seek(offset)
   dev.checkGuard(file, size)
   print('Updating from version %s to version %s' % dev.getFirmwareVersion())

   try:
    dev.switchMode()
    print('Switching to updater mode')
    print('Please press Ok to reset the camera, then run this command again to install the firmware')

   except SonyUpdaterSequenceError:
    def progress(written, total):
     p = int(written * 20 / total) * 5
     if p != progress.percent:
      print('%d%%' % p)
      progress.percent = p
    progress.percent = -1

    print('Writing firmware')
    file.seek(offset)
    dev.writeFirmware(file, size, progress)
    dev.complete()
    print('Done')
