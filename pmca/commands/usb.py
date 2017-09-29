from __future__ import print_function
import io
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
from ..usb import usbshell
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


appListCache = None
def listApps(enableCache=False):
 global appListCache
 remoteAppStore = RemoteAppStore(config.appengineServer)
 appStoreRepo = appstore.GithubApi(config.githubAppListUser, config.githubAppListRepo)

 if not appListCache or not enableCache:
  print('Loading app list')
  try:
   apps = remoteAppStore.listApps()
  except:
   print('Cannot connect to remote server, falling back to appstore repository')
   apps = appstore.AppStore(appStoreRepo).apps
  print('Found %d apps' % len(apps))
  appListCache = apps
 return appListCache


def installApp(dev, apkFile=None, appPackage=None, outFile=None, local=False):
 """Installs an app on the specified device."""
 certFile = scriptRoot + '/certs/localtest.me.pem'
 with ServerContext(LocalMarketServer(certFile, config.officialServer)) as server:
  if apkFile:
   server.setApk(apkFile.read())
  elif appPackage:
   print('Downloading apk')
   apps = listApps(True)
   if appPackage not in apps:
    raise Exception('Unknown app: %s' % appPackage)
   server.setApk(apps[appPackage].release.asset)

  print('Starting task')
  xpdData = server.getXpd()

  print('Starting communication')
  # Point the camera to the web api
  result = installer.install(dev, server.host, server.port, xpdData, printStatus)
  if result.code != 0:
   raise Exception('Communication error %d: %s' % (result.code, result.message))

  result = server.getResult()

  if not local:
   try:
    RemoteAppStore(config.appengineServer).sendStats(result)
   except:
    pass

  print('Task completed successfully')

  if outFile:
   print('Writing to output file')
   json.dump(result, outFile, indent=2)

  return result


class UsbDriverList:
 def __init__(self, *contexts):
  self._contexts = contexts
  self._drivers = []

 def __enter__(self):
  self._drivers = [context.__enter__() for context in self._contexts]
  return self

 def __exit__(self, *ex):
  for context in self._contexts:
   context.__exit__(*ex)
  self._drivers = []

 def listDevices(self, vendor):
  for driver in self._drivers:
   for dev in driver.listDevices(vendor):
    yield dev, driver.classType, driver.openDevice(dev)


def importDriver(driverName=None):
 """Imports the usb driver. Use in a with statement"""
 MscContext = None
 MtpContext = None

 # Load native drivers
 if driverName == 'native' or driverName is None:
  if sys.platform == 'win32':
   from ..usb.driver.windows.msc import MscContext
   from ..usb.driver.windows.wpd import MtpContext
  elif sys.platform == 'darwin':
   from ..usb.driver.osx import MscContext
  else:
   print('No native drivers available')
 elif driverName != 'libusb':
  raise Exception('Unknown driver')

 # Fallback to libusb
 if MscContext is None:
  from ..usb.driver.libusb import MscContext
 if MtpContext is None:
  from ..usb.driver.libusb import MtpContext

 drivers = [MscContext(), MtpContext()]
 print('Using drivers %s' % ', '.join(d.name for d in drivers))
 return UsbDriverList(*drivers)


def listDevices(driverList, quiet=False):
 """List all Sony usb devices"""
 if not quiet:
  print('Looking for Sony devices')
 for dev, type, drv in driverList.listDevices(SONY_ID_VENDOR):
  if type == USB_CLASS_MSC:
   if not quiet:
    print('\nQuerying mass storage device')
   # Get device info
   info = MscDevice(drv).getDeviceInfo()

   if isSonyMscCamera(info):
    if isSonyUpdaterCamera(dev):
     if not quiet:
      print('%s %s is a camera in updater mode' % (info.manufacturer, info.model))
     yield SonyMscUpdaterCamera(drv)
    else:
     if not quiet:
      print('%s %s is a camera in mass storage mode' % (info.manufacturer, info.model))
     yield SonyMscCamera(drv)

  elif type == USB_CLASS_PTP:
   if not quiet:
    print('\nQuerying MTP device')
   # Get device info
   info = MtpDevice(drv).getDeviceInfo()

   if isSonyMtpCamera(info):
    if not quiet:
     print('%s %s is a camera in MTP mode' % (info.manufacturer, info.model))
    yield SonyMtpCamera(drv)
   elif isSonyMtpAppInstaller(info):
    if not quiet:
     print('%s %s is a camera in app install mode' % (info.manufacturer, info.model))
    yield SonyMtpAppInstaller(drv)
  if not quiet:
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


def infoCommand(driverName=None):
 """Display information about the camera connected via usb"""
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if isinstance(device, SonyMtpAppInstaller):
    info = installApp(device)
    print('')
    props = [
     ('Model', info['deviceinfo']['name']),
     ('Product code', info['deviceinfo']['productcode']),
     ('Serial number', info['deviceinfo']['deviceid']),
     ('Firmware version', info['deviceinfo']['fwversion']),
    ]
   else:
    info = SonyExtCmdCamera(device).getCameraInfo()
    updater = SonyUpdaterCamera(device)
    updater.init()
    firmwareOld, firmwareNew = updater.getFirmwareVersion()
    props = [
     ('Model', info.modelName),
     ('Product code', info.modelCode),
     ('Serial number', info.serial),
     ('Firmware version', firmwareOld),
    ]
   for k, v in props:
    print('%-20s%s' % (k + ': ', v))


def installCommand(driverName=None, apkFile=None, appPackage=None, outFile=None, local=False):
 """Install the given apk on the camera"""
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device and not isinstance(device, SonyMtpAppInstaller):
   switchToAppInstaller(device)
   device = None

   print('Waiting for camera to switch...')
   for i in range(10):
    time.sleep(.5)
    try:
     devices = list(listDevices(driver, True))
     if len(devices) == 1 and isinstance(devices[0], SonyMtpAppInstaller):
      device = devices[0]
      break
    except:
     pass
   else:
    print('Operation timed out. Please run this command again when your camera has connected.')

  if device:
   installApp(device, apkFile, appPackage, outFile, local)


def appSelectionCommand():
 apps = list(listApps().values())
 for i, app in enumerate(apps):
  print(' [%2d] %s' % (i+1, app.package))
 i = int(input('Enter number of app to install (0 to abort): '))
 if i != 0:
  pkg = apps[i - 1].package
  print('')
  print('Installing %s' % pkg)
  return pkg


def getFdats():
 fdatDir = scriptRoot + '/updatershell/fdat/'
 for dir in os.listdir(fdatDir):
  if os.path.isdir(fdatDir + dir):
   payloadFile = fdatDir + dir + '.dat'
   if os.path.isfile(payloadFile):
    for model in os.listdir(fdatDir + dir):
     hdrFile = fdatDir + dir + '/' + model
     if os.path.isfile(hdrFile) and hdrFile.endswith('.hdr'):
      yield model[:-4], (hdrFile, payloadFile)


def getFdat(device):
 fdats = dict(getFdats())
 if device.endswith('V') and device not in fdats:
  device = device[:-1]
 if device in fdats:
  hdrFile, payloadFile = fdats[device]
  with open(hdrFile, 'rb') as hdr, open(payloadFile, 'rb') as payload:
   return hdr.read() + payload.read()


def firmwareUpdateCommand(file, driverName=None):
 offset, size = firmware.readDat(file)

 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   firmwareUpdateCommandInternal(driver, device, file, offset, size)


def updaterShellCommand(model=None, fdatFile=None, driverName=None):
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if fdatFile:
    fdat = fdatFile.read()
   else:
    if not model:
     print('Getting device info')
     model = SonyExtCmdCamera(device).getCameraInfo().modelName
     print('Using firmware for model %s' % model)
     print('')

    fdat = getFdat(model)
    if not fdat:
     print('Unknown device: %s' % model)
     return

   def complete():
    print('Starting updater shell...')
    print('')
    usbshell.usbshell_loop(device)
   firmwareUpdateCommandInternal(driver, device, io.BytesIO(fdat), 0, len(fdat), complete)


def firmwareUpdateCommandInternal(driver, device, file, offset, size, complete=None):
 if isinstance(device, SonyMtpAppInstaller):
  print('Error: Cannot use camera in app install mode. Please restart the device.')
  return

 dev = SonyUpdaterCamera(device)

 print('Initializing firmware update')
 dev.init()
 file.seek(offset)
 dev.checkGuard(file, size)
 versions = dev.getFirmwareVersion()
 if versions[1] != '9.99':
  print('Updating from version %s to version %s' % versions)

 if not isinstance(device, SonyMscUpdaterCamera):
  print('Switching to updater mode')
  dev.switchMode()
  print('Please follow the instructions on the camera screen')

  device = None
  print('')
  print('Waiting for camera to switch...')
  for i in range(60):
   time.sleep(.5)
   try:
    devices = list(listDevices(driver, True))
    if len(devices) == 1 and isinstance(devices[0], SonyMscUpdaterCamera):
     device = devices[0]
     break
   except:
    pass
  else:
   print('Operation timed out. Please run this command again when your camera has connected.')

  if device:
   firmwareUpdateCommandInternal(None, device, file, offset, size, complete)

 else:
  def progress(written, total):
   p = int(written * 20 / total) * 5
   if p != progress.percent:
    print('%d%%' % p)
    progress.percent = p
  progress.percent = -1

  print('Writing firmware')
  file.seek(offset)
  dev.writeFirmware(file, size, progress, complete)
  dev.complete()
  print('Done')
