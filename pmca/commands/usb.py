import io
import json
import os
import sys
import time
import struct
import zipfile

import config
from ..apk import *
from .. import appstore
from .. import firmware
from .. import installer
from ..io import *
from ..marketserver.server import *
from ..usb import *
from ..usb.driver import *
from ..usb.driver.generic import *
from ..usb.sensershell import *
from ..usb.sony import *
from ..usb.usbshell import *
from ..util import http

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
 appStoreRepo = appstore.GithubApi(config.githubAppListUser, config.githubAppListRepo)

 if not appListCache or not enableCache:
  print('Loading app list')
  apps = appstore.AppStore(appStoreRepo).apps
  print('Found %d apps' % len(apps))
  appListCache = apps
 return appListCache


def installApp(dev, apkFile=None, appPackage=None, outFile=None):
 """Installs an app on the specified device."""
 certFile = scriptRoot + '/certs/localtest.me.pem'
 with ServerContext(LocalMarketServer(certFile)) as server:
  apkData = None
  if apkFile:
   apkData = apkFile.read()
  elif appPackage:
   print('Downloading apk')
   apps = listApps(True)
   if appPackage not in apps:
    raise Exception('Unknown app: %s' % appPackage)
   apkData = apps[appPackage].release.asset

  if apkData:
   print('Analyzing apk')
   print('')
   checkApk(io.BytesIO(apkData))
   print('')
   server.setApk(apkData)

  print('Starting task')
  xpdData = server.getXpd()

  print('Starting communication')
  # Point the camera to the web api
  result = installer.install(SonyAppInstallCamera(dev), server.host, server.port, xpdData, printStatus)
  if result.code != 0:
   raise Exception('Communication error %d: %s' % (result.code, result.message))

  result = server.getResult()

  print('Task completed successfully')

  if outFile:
   print('Writing to output file')
   json.dump(result, outFile, indent=2)

  return result


def checkApk(apkFile):
 try:
  apk = ApkParser(apkFile)

  props = [
   ('Package', apk.getPackageName()),
   ('Version', apk.getVersionName()),
  ]
  apk.getVersionCode()
  for k, v in props:
   print('%-9s%s' % (k + ': ', v))

  sdk = apk.getMinSdkVersion()
  if sdk > 10:
   print('Warning: This app might not be compatible with the device (minSdkVersion = %d)' % sdk)

  try:
   apk.getCert()
  except:
   print('Warning: Cannot read apk certificate')

 except:
  print('Warning: Invalid apk file')


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
 VendorSpecificContext = None
 MscContext2 = None
 MtpContext2 = None
 VendorSpecificContext2 = None

 # Load native drivers
 if driverName == 'native' or driverName is None:
  if sys.platform == 'win32':
   from ..usb.driver.windows.msc import MscContext
   from ..usb.driver.windows.wpd import MtpContext
   from ..usb.driver.windows.driverless import VendorSpecificContext
  elif sys.platform == 'darwin':
   from ..usb.driver.osx import isMscDriverAvailable
   if isMscDriverAvailable():
    from ..usb.driver.osx import MscContext
   else:
    print('Native driver not installed')
  else:
   print('No native drivers available')
 elif driverName == 'qemu':
  from ..usb.driver.generic.qemu import MscContext
  from ..usb.driver.generic.qemu import MtpContext
 elif driverName != 'libusb':
  raise Exception('Unknown driver')

 # Fallback to libusb
 if MscContext is None or (driverName is None and sys.platform == 'win32'):
  from ..usb.driver.generic.libusb import MscContext as MscContext2
 if MtpContext is None or (driverName is None and sys.platform == 'win32'):
  from ..usb.driver.generic.libusb import MtpContext as MtpContext2
 if (VendorSpecificContext is None and driverName != 'qemu') or (driverName is None and sys.platform == 'win32'):
  from ..usb.driver.generic.libusb import VendorSpecificContext as VendorSpecificContext2

 drivers = [context() for context in [MscContext, MtpContext, VendorSpecificContext, MscContext2, MtpContext2, VendorSpecificContext2] if context]
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
    if isSonyMscUpdaterCamera(dev):
     if not quiet:
      print('%s %s is a camera in updater mode' % (info.manufacturer, info.model))
     yield SonyMscUpdaterDevice(drv)
    else:
     if not quiet:
      print('%s %s is a camera in mass storage mode' % (info.manufacturer, info.model))
     yield SonyMscExtCmdDevice(drv)

  elif type == USB_CLASS_PTP:
   if not quiet:
    print('\nQuerying MTP device')
   # Get device info
   info = MtpDevice(drv).getDeviceInfo()

   if isSonyMtpCamera(info):
    if not quiet:
     print('%s %s is a camera in MTP mode' % (info.manufacturer, info.model))
    yield SonyMtpExtCmdDevice(drv)
   elif isSonyMtpAppInstallCamera(info):
    if not quiet:
     print('%s %s is a camera in app install mode' % (info.manufacturer, info.model))
    yield SonyMtpAppInstallDevice(drv)

  elif type == USB_CLASS_VENDOR_SPECIFIC:
   if isSonySenserCamera(dev):
    print('Found a camera in service mode')
    yield SonySenserDevice(drv)

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
   if isinstance(device, SonyAppInstallDevice):
    info = installApp(device)
    print('')
    props = [
     ('Model', info['deviceinfo']['name']),
     ('Product code', info['deviceinfo']['productcode']),
     ('Serial number', info['deviceinfo']['deviceid']),
     ('Firmware version', info['deviceinfo']['fwversion']),
    ]
   elif isinstance(device, SonyExtCmdDevice):
    dev = SonyExtCmdCamera(device)
    info = dev.getCameraInfo()
    updater = SonyUpdaterCamera(device)
    updater.init()
    firmwareOld, firmwareNew = updater.getFirmwareVersion()
    props = [
     ('Model', info.modelName),
     ('Product code', info.modelCode),
     ('Serial number', info.serial),
     ('Firmware version', firmwareOld),
    ]
    try:
     lensInfo = dev.getLensInfo()
     if lensInfo.model != 0:
      props.append(('Lens', 'Model 0x%x (Firmware %s)' % (lensInfo.model, lensInfo.version)))
    except (InvalidCommandException, UnknownMscException):
     pass
    try:
     gpsInfo = dev.getGpsData()
     props.append(('GPS Data', '%s - %s' % gpsInfo))
    except (InvalidCommandException, UnknownMscException):
     pass
   else:
    print('Error: Cannot use camera in this mode.')
    return
   for k, v in props:
    print('%-20s%s' % (k + ': ', v))


def installCommand(driverName=None, apkFile=None, appPackage=None, outFile=None):
 """Install the given apk on the camera"""
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device and isinstance(device, SonyExtCmdDevice):
   switchToAppInstaller(device)
   device = None

   print('Waiting for camera to switch...')
   for i in range(10):
    time.sleep(.5)
    try:
     devices = list(listDevices(driver, True))
     if len(devices) == 1 and isinstance(devices[0], SonyAppInstallDevice):
      device = devices[0]
      break
    except:
     pass
   else:
    print('Operation timed out. Please run this command again when your camera has connected.')

  if device and isinstance(device, SonyAppInstallDevice):
   installApp(device, apkFile, appPackage, outFile)
  elif device:
   print('Error: Cannot use camera in this mode.')


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
 while device != '' and not device[-1:].isdigit() and device not in fdats:
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


def updaterShellCommand(model=None, fdatFile=None, driverName=None, complete=None):
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if fdatFile:
    fdat = fdatFile.read()
   else:
    if not model:
     print('Getting device info')
     try:
      model = SonyExtCmdCamera(device).getCameraInfo().modelName
     except:
      print('Error: Cannot determine camera model')
      return
     print('Using firmware for model %s' % model)
     print('')

    fdat = getFdat(model)
    if not fdat:
     print('Unknown device: %s' % model)
     return

   if not complete:
    def complete(device):
     print('Starting updater shell...')
     print('')
     UpdaterShell(device).run()
   firmwareUpdateCommandInternal(driver, device, io.BytesIO(fdat), 0, len(fdat), complete)


def firmwareUpdateCommandInternal(driver, device, file, offset, size, complete=None):
 if not isinstance(device, SonyUpdaterDevice) and not isinstance(device, SonyExtCmdDevice):
  print('Error: Cannot use camera in this mode.')
  return

 dev = SonyUpdaterCamera(device)

 print('Initializing firmware update')
 dev.init()
 file.seek(offset)
 dev.checkGuard(file, size)
 versions = dev.getFirmwareVersion()
 if versions[1] != '9.99':
  print('Updating from version %s to version %s' % versions)

 if not isinstance(device, SonyUpdaterDevice):
  print('Switching to updater mode')
  dev.switchMode()

  device = None
  print('')
  print('Waiting for camera to switch...')
  print('Please follow the instructions on the camera screen.')
  for i in range(60):
   time.sleep(.5)
   try:
    devices = list(listDevices(driver, True))
    if len(devices) == 1 and isinstance(devices[0], SonyUpdaterDevice):
     device = devices[0]
     break
   except:
    pass
  else:
   print('Operation timed out. Please run this command again when your camera has connected.')

  if device:
   firmwareUpdateCommandInternal(None, device, file, offset, size, complete)

 else:
  print('Writing firmware')
  file.seek(offset)
  dev.writeFirmware(ProgressFile(file, size), size, complete)
  dev.complete()
  print('Done')


def guessFirmwareCommand(file, driverName=None):
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if not isinstance(device, SonyExtCmdDevice):
    print('Error: Cannot use camera in this mode.')
    return

   print('Getting device info')
   model = SonyExtCmdCamera(device).getCameraInfo().modelName
   print('Model name: %s' % model)
   print('')

   dev = SonyUpdaterCamera(device)
   with zipfile.ZipFile(file) as zip:
    infos = zip.infolist()
    print('Trying %d firmware images' % len(infos))
    for info in infos:
     data = zip.read(info)
     try:
      dev.init()
      dev.checkGuard(io.BytesIO(data), len(data))
      break
     except Exception as e:
      if 'Invalid model' not in str(e):
       print(e)
       break
    else:
     print('Fail: No matching file found')
     return
    print('Success: Found matching file: %s' % info.filename)


def gpsUpdateCommand(file=None, driverName=None):
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if not isinstance(device, SonyExtCmdDevice):
    print('Error: Cannot use camera in this mode.')
    return

   if not file:
    print('Downloading GPS data')
    file = io.BytesIO(http.get('https://control.d-imaging.sony.co.jp/GPS/assistme.dat').raw_data)

   print('Writing GPS data')
   SonyExtCmdCamera(device).writeGpsData(file)
   print('Done')


def streamingCommand(write=None, file=None, driverName=None):
 """Read/Write Streaming information for the camera connected via usb"""
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if not isinstance(device, SonyExtCmdDevice):
    print('Error: Cannot use camera in this mode.')
   else:
    dev = SonyExtCmdCamera(device)

    if write:
     incoming = json.load(write)

     # assemble Social (first 9 items in file)
     mydict = {}
     for key in incoming[:9]:
      if key[0] in ['twitterEnabled', 'facebookEnabled']:
       mydict[key[0]] = key[1] # Integer
      else:
       mydict[key[0]] = key[1].encode('ascii')

     data = SonyExtCmdCamera.LiveStreamingSNSInfo.pack(
      twitterEnabled = mydict['twitterEnabled'],
      twitterConsumerKey = mydict['twitterConsumerKey'].ljust(1025, b'\x00'),
      twitterConsumerSecret = mydict['twitterConsumerSecret'].ljust(1025, b'\x00'),
      twitterAccessToken1 = mydict['twitterAccessToken1'].ljust(1025, b'\x00'),
      twitterAccessTokenSecret = mydict['twitterAccessTokenSecret'].ljust(1025, b'\x00'),
      twitterMessage = mydict['twitterMessage'].ljust(401, b'\x00'),
      facebookEnabled = mydict['facebookEnabled'],
      facebookAccessToken = mydict['facebookAccessToken'].ljust(1025, b'\x00'),
      facebookMessage = mydict['facebookMessage'].ljust(401, b'\x00'),
     )
     dev.setLiveStreamingSocialInfo(data)

     # assemble Streaming, file may contain multiple sets (of 14 items)
     data = b'\x01\x00\x00\x00'
     data += struct.pack('<i', int((len(incoming)-9)/14))
     mydict = {}
     count = 1
     for key in incoming[9:]:
      if key[0] in ['service', 'enabled', 'videoFormat', 'videoFormat', 'unknown', \
        'enableRecordMode', 'channels', 'supportedFormats']:
       mydict[key[0]] = key[1]
      elif key[0] == 'macIssueTime':
       mydict[key[0]] = binascii.a2b_hex(key[1])
      else:
       mydict[key[0]] = key[1].encode('ascii')

      if count == 14:
       # reassemble Structs
       data += SonyExtCmdCamera.LiveStreamingServiceInfo1.pack(
        service = mydict['service'],
        enabled = mydict['enabled'],
        macId = mydict['macId'].ljust(41, b'\x00'),
        macSecret = mydict['macSecret'].ljust(41, b'\x00'),
        macIssueTime = mydict['macIssueTime'],
        unknown = 0, # mydict['unknown'],
       )

       data += struct.pack('<i', len(mydict['channels']))
       for j in range(len(mydict['channels'])):
        data += struct.pack('<i', mydict['channels'][j])

       data += SonyExtCmdCamera.LiveStreamingServiceInfo2.pack(
        shortURL = mydict['shortURL'].ljust(101, b'\x00'),
        videoFormat = mydict['videoFormat'],
       )

       data += struct.pack('<i', len(mydict['supportedFormats']))
       for j in range(len(mydict['supportedFormats'])):
        data += struct.pack('<i', mydict['supportedFormats'][j])

       data += SonyExtCmdCamera.LiveStreamingServiceInfo3.pack(
        enableRecordMode = mydict['enableRecordMode'],
        videoTitle = mydict['videoTitle'].ljust(401, b'\x00'),
        videoDescription = mydict['videoDescription'].ljust(401, b'\x00'),
        videoTag = mydict['videoTag'].ljust(401, b'\x00'),
       )
       count = 1
      else:
       count += 1

     dev.setLiveStreamingServiceInfo(data)
     return

    # Read settings from camera (do this first so we know channels/supportedFormats)
    settings = dev.getLiveStreamingServiceInfo()
    social = dev.getLiveStreamingSocialInfo()

    data = []
    # Social settings
    for key in (social._asdict()).items():
     if key[0] in ['twitterEnabled', 'facebookEnabled']:
      data.append([key[0], key[1]])
     else:
      data.append([key[0], key[1].decode('ascii').split('\x00')[0]])

    # Streaming settings, file may contain muliple sets of data
    try:
     for key in next(settings).items():
      if key[0] in ['service', 'enabled', 'videoFormat', 'enableRecordMode', \
        'unknown', 'channels', 'supportedFormats']:
       data.append([key[0], key[1]])
      elif key[0] == 'macIssueTime':
       data.append([key[0], binascii.b2a_hex(key[1]).decode('ascii')])
      else:
       data.append([key[0], key[1].decode('ascii').split('\x00')[0]])
    except StopIteration:
     pass

    if file:
     file.write(json.dumps(data, indent=4))
    else:
     for k, v in data:
      print('%-20s%s' % (k + ': ', v))


def wifiCommand(write=None, file=None, multi=False, driverName=None):
 """Read/Write WiFi information for the camera connected via usb"""
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device:
   if not isinstance(device, SonyExtCmdDevice):
    print('Error: Cannot use camera in this mode.')
   else:
    dev = SonyExtCmdCamera(device)

    if write:
     incoming = json.load(write)
     data = struct.pack('<i', int(len(incoming)/3))

     mydict = {}
     count = 1
     for key in incoming:
      if key[0] == 'keyType':
       mydict[key[0]] = key[1] # Integer
      else:
       mydict[key[0]] = key[1].encode('ascii')

      if count == 3:
       # reassemble Struct
       apinfo = SonyExtCmdCamera.APInfo.pack(
        keyType = mydict['keyType'],
        sid = mydict['sid'].ljust(33, b'\x00'),
        key = mydict['key'].ljust(65, b'\x00'),
       )
       data += apinfo
       count = 1
      else:
       count += 1

     if multi:
      dev.setMultiWifiAPInfo(data)
     else:
      dev.setWifiAPInfo(data)
     return

    # Read settings from camera
    if multi:
     settings = dev.getMultiWifiAPInfo()
    else:
     settings = dev.getWifiAPInfo()

    data = []
    try:
     for key in next(settings)._asdict().items():
      if key[0] == 'keyType':
       data.append([key[0], key[1]]) # Integer
      else:
       data.append([key[0],key[1].decode('ascii').split('\x00')[0]])
    except StopIteration:
     pass

    if file:
     file.write(json.dumps(data, indent=4))
    else:
     for k, v in data:
      print('%-20s%s' % (k + ': ', v))


def senserShellCommand(driverName=None):
 if driverName is None and sys.platform != 'win32':
  driverName = 'libusb'
 with importDriver(driverName) as driver:
  device = getDevice(driver)
  if device and isinstance(device, SonyMscExtCmdDevice):
   if not isinstance(device.driver, GenericUsbDriver):
    print('Error: Only libusb drivers are supported for service mode')
    return

   print('Switching to service mode')
   dev = SonySenserAuthDevice(device.driver)
   dev.start()
   dev.authenticate()

   device = None
   print('')
   print('Waiting for camera to switch...')
   for i in range(10):
    time.sleep(.5)
    try:
     devices = list(listDevices(driver, True))
     if len(devices) == 1 and isinstance(devices[0], SonySenserDevice):
      device = devices[0]
      break
    except:
     pass
   else:
    print('Operation timed out. Please run this command again when your camera has connected.')

  if device and isinstance(device, SonySenserDevice):
   if not isinstance(device.driver, GenericUsbDriver):
    print('Error: Only libusb drivers are supported for service mode')
    return

   print('Authenticating')
   dev = SonySenserAuthDevice(device.driver)
   dev.start()
   dev.authenticate()
   try:
    SenserShell(SonySenserCamera(device)).run()
   finally:
    dev.stop()
   print('Done')
  elif device:
   print('Error: Cannot use camera in this mode.')
