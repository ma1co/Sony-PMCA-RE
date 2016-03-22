#!/usr/bin/env python
"""A command line application to install apps on Android-enabled Sony cameras"""

import argparse
import json
import os
import sys

from pmca import installer
from pmca.marketserver.server import *
from pmca.usb import *
from pmca.usb.driver import *
from pmca.usb.sony import *

def printStatus(status):
 """Print progress"""
 print '%s %d%%' % (status.message, status.percent)

def switchToAppInstaller(dev):
 """Switches a camera in MTP mode to app installation mode"""
 print 'Switching to app install mode. Please run this command again when the camera has switched modes.'
 SonyExtCmdCamera(dev).switchToAppInstaller()

defaultCertFile = getattr(sys, '_MEIPASS', 'certs') + '/localtest.me.pem'
def installApp(dev, host=None, apkFile=None, outFile=None, certFile=defaultCertFile):
 """Installs an app on the specified device."""
 apkData = apkFile.read() if apkFile else None

 if host:
  server = RemoteMarketServer(host, apkData)
 else:
  server = LocalMarketServer(certFile, apkData)

 print ('Uploading apk' if apkData else 'Starting task') if host else 'Starting server'
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
 devices = [dev for dev in driver.listDevices() if dev.idVendor == SONY_ID_VENDOR]

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


def main():
 """Command line main"""
 parser = argparse.ArgumentParser()
 subparsers = parser.add_subparsers(dest='command', title='commands')
 install = subparsers.add_parser('install', description='Installs an apk file on the camera connected via USB. The connection can be tested without specifying a file.')
 install.add_argument('-s', dest='server', help='hostname for the remote server (set to empty to start a local server)', default='sony-pmca.appspot.com')
 install.add_argument('-d', dest='driver', choices=['libusb', 'windows'], help='specify the driver')
 install.add_argument('-o', dest='outFile', type=argparse.FileType('w'), help='write the output to this file')
 install.add_argument('-f', dest='apkFile', type=argparse.FileType('rb'), help='the apk file to install')

 args = parser.parse_args()
 if args.command == 'install':
  installCommand(args.server, args.driver, args.apkFile, args.outFile)


if __name__ == '__main__':
 main()
