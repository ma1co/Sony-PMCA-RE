#!/usr/bin/env python
"""A command line application to install apps on Android-enabled Sony cameras"""

import argparse
import json
import os

from pmca import installer
from pmca.api import *
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

def installApp(dev, api, apkFile=None, outFile=None):
 """Installs an app on the specified device. The apk is uploaded to the specified WebApi."""
 print 'Creating task'
 # Upload apk (if any), start task
 task = api.startBlobTask(api.uploadBlob(apkFile.read())) if apkFile else api.startTask()
 xpdData = api.getXpd(task)

 print 'Starting communication'
 # Point the camera to the web api
 result = installer.install(dev, xpdData, printStatus)
 if result.code != 0:
  raise Exception('Communication error %d: %s' % (result.code, result.message))

 print 'Downloading task'
 # Get the result from the website
 result = api.getTask(task)
 if not result['completed']:
  raise Exception('Task was not completed')
 result = result['response']

 print 'Task completed successfully'

 if outFile:
  print 'Writing to output file'
  json.dump(result, outFile, indent=2)


def installCommand(url, driverName=None, apkFile=None, outFile=None):
 """Install command main"""
 if not driverName:
  # On Windows, we default to wpd, user libusb for other systems
  driverName = 'wpd' if os.name == 'nt' else 'libusb'

 # Import the specified driver
 if driverName == 'libusb':
  print 'Using libusb'
  import pmca.usb.driver.libusb as driver
 elif driverName == 'wpd':
  print 'Using Windows Portable Device Api (WPD)'
  import pmca.usb.driver.wpd as driver
 else:
  raise Exception('Unknown driver')

 print 'Looking for Sony MTP devices'
 # Scan for MTP devices
 devices = [dev for dev in driver.listDevices() if dev.type == USB_CLASS_PTP and dev.idVendor == SONY_ID_VENDOR]

 if not devices:
  print 'No MTP devices found. Ensure your camera is connected in MTP mode.'

 for device in devices:
  print '\nQuerying device'
  # Get device info
  drv = driver.MtpDriver(device)
  info = MtpDevice(drv).getDeviceInfo()

  if isSonyMtpCamera(info):
   print '%s is a camera in MTP mode' % info.model
   switchToAppInstaller(SonyMtpCamera(drv))
  elif isSonyMtpAppInstaller(info):
   print '%s is a camera in app install mode' % info.model
   installApp(SonyMtpAppInstaller(drv), WebApi(url), apkFile, outFile)


def main():
 """Command line main"""
 parser = argparse.ArgumentParser()
 subparsers = parser.add_subparsers(dest='command', title='commands')
 install = subparsers.add_parser('install', description='Installs an apk file on the camera connected via USB. The connection can be tested without specifying a file.')
 install.add_argument('-u', dest='url', help='specify the web api base url', default='https://sony-pmca.appspot.com')
 install.add_argument('-d', dest='driver', choices=['libusb', 'wpd'], help='specify the driver')
 install.add_argument('-o', dest='outFile', type=argparse.FileType('w'), help='write the output to this file')
 install.add_argument('-f', dest='apkFile', type=argparse.FileType('rb'), help='the apk file to install')

 args = parser.parse_args()
 if args.command == 'install':
  installCommand(args.url, args.driver, args.apkFile, args.outFile)


if __name__ == '__main__':
 main()
