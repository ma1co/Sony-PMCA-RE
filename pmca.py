#!/usr/bin/env python
"""A command line application to install apps on Android-enabled Sony cameras"""

import argparse
from getpass import getpass
import json
import os, os.path
import re
import sys

from pmca import installer
from pmca import marketclient
from pmca.marketserver.server import *
from pmca import spk
from pmca.usb import *
from pmca.usb.driver import *
from pmca.usb.sony import *

scriptRoot = getattr(sys, '_MEIPASS', os.path.dirname(__file__))

def printStatus(status):
 """Print progress"""
 print '%s %d%%' % (status.message, status.percent)

def switchToAppInstaller(dev):
 """Switches a camera in MTP mode to app installation mode"""
 print 'Switching to app install mode. Please run this command again when the camera has switched modes.'
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


def installCommand(host=None, driverName=None, apkFile=None, outFile=None):
 """Install command main"""
 if not driverName:
  driverName = 'windows' if os.name == 'nt' else 'libusb'

 # Import the specified driver
 if driverName == 'libusb':
  print 'Using libusb'
  import pmca.usb.driver.libusb as driver
 elif driverName == 'windows':
  print 'Using Windows drivers'
  import pmca.usb.driver.windows as driver
 else:
  raise Exception('Unknown driver')

 print 'Looking for Sony devices'
 # Scan for devices
 devices = list(driver.listDevices(SONY_ID_VENDOR))

 if not devices:
  print 'No devices found. Ensure your camera is connected.'

 for device in devices:
  if device.type == USB_CLASS_MSC:
   print '\nQuerying mass storage device'
   # Get device info
   drv = driver.MscDriver(device)
   info = MscDevice(drv).getDeviceInfo()

   if isSonyMscCamera(info):
    print '%s %s is a camera in mass storage mode' % (info.manufacturer, info.model)
    switchToAppInstaller(SonyMscCamera(drv))

  elif device.type == USB_CLASS_PTP:
   print '\nQuerying MTP device'
   # Get device info
   drv = driver.MtpDriver(device)
   info = MtpDevice(drv).getDeviceInfo()

   if isSonyMtpCamera(info):
    print '%s %s is a camera in MTP mode' % (info.manufacturer, info.model)
    switchToAppInstaller(SonyMtpCamera(drv))
   elif isSonyMtpAppInstaller(info):
    print '%s %s is a camera in app install mode' % (info.manufacturer, info.model)
    installApp(SonyMtpAppInstaller(drv), host, apkFile, outFile)


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
  for app in marketclient.getApps(device.deviceid):
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


def main():
 """Command line main"""
 parser = argparse.ArgumentParser()
 subparsers = parser.add_subparsers(dest='command', title='commands')
 install = subparsers.add_parser('install', description='Installs an apk file on the camera connected via USB. The connection can be tested without specifying a file.')
 install.add_argument('-s', dest='server', help='hostname for the remote server (set to empty to start a local server)', default='sony-pmca.appspot.com')
 install.add_argument('-d', dest='driver', choices=['libusb', 'windows'], help='specify the driver')
 install.add_argument('-o', dest='outFile', type=argparse.FileType('w'), help='write the output to this file')
 install.add_argument('-f', dest='apkFile', type=argparse.FileType('rb'), help='the apk file to install')
 market = subparsers.add_parser('market', description='Download apps from the official Sony app store')
 market.add_argument('-t', dest='token', help='Specify an auth token')
 market = subparsers.add_parser('apk2spk', description='Convert apk to spk')
 market.add_argument('inFile', metavar='app.apk', type=argparse.FileType('rb'), help='the apk file to convert')
 market.add_argument('outFile', metavar='app' + spk.constants.extension, type=argparse.FileType('wb'), help='the output spk file')
 market = subparsers.add_parser('spk2apk', description='Convert spk to apk')
 market.add_argument('inFile', metavar='app' + spk.constants.extension, type=argparse.FileType('rb'), help='the spk file to convert')
 market.add_argument('outFile', metavar='app.apk', type=argparse.FileType('wb'), help='the output apk file')

 args = parser.parse_args()
 if args.command == 'install':
  installCommand(args.server, args.driver, args.apkFile, args.outFile)
 elif args.command == 'market':
  marketCommand(args.token)
 elif args.command == 'apk2spk':
  args.outFile.write(spk.dump(args.inFile.read()))
 elif args.command == 'spk2apk':
  args.outFile.write(spk.parse(args.inFile.read()))


if __name__ == '__main__':
 main()
