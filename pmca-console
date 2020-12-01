#!/usr/bin/env python3
"""A command line application to install apps on Android-enabled Sony cameras"""
import argparse

from pmca.commands.market import *
from pmca.commands.usb import *
from pmca import spk

if getattr(sys, 'frozen', False):
 from frozenversion import version
else:
 version = None

def main():
 """Command line main"""
 parser = argparse.ArgumentParser()
 if version:
  parser.add_argument('--version', action='version', version=version)
 drivers = ['native', 'libusb', 'qemu']
 subparsers = parser.add_subparsers(dest='command', title='commands')
 info = subparsers.add_parser('info', description='Display information about the camera connected via USB')
 info.add_argument('-d', dest='driver', choices=drivers, help='specify the driver')
 install = subparsers.add_parser('install', description='Installs an apk file on the camera connected via USB. The connection can be tested without specifying a file.')
 install.add_argument('-d', dest='driver', choices=drivers, help='specify the driver')
 install.add_argument('-o', dest='outFile', type=argparse.FileType('w'), help='write the output to this file')
 install.add_argument('-l', dest='local', action='store_true', help='local only (don\'t send statistics)')
 installMode = install.add_mutually_exclusive_group()
 installMode.add_argument('-f', dest='apkFile', type=argparse.FileType('rb'), help='install an apk file')
 installMode.add_argument('-a', dest='appPackage', help='the package name of an app from the app list')
 installMode.add_argument('-i', dest='appInteractive', action='store_true', help='select an app from the app list (interactive)')
 market = subparsers.add_parser('market', description='Download apps from the official Sony app store')
 market.add_argument('-t', dest='token', help='Specify an auth token')
 apk2spk = subparsers.add_parser('apk2spk', description='Convert apk to spk')
 apk2spk.add_argument('inFile', metavar='app.apk', type=argparse.FileType('rb'), help='the apk file to convert')
 apk2spk.add_argument('outFile', metavar='app' + spk.constants.extension, type=argparse.FileType('wb'), help='the output spk file')
 spk2apk = subparsers.add_parser('spk2apk', description='Convert spk to apk')
 spk2apk.add_argument('inFile', metavar='app' + spk.constants.extension, type=argparse.FileType('rb'), help='the spk file to convert')
 spk2apk.add_argument('outFile', metavar='app.apk', type=argparse.FileType('wb'), help='the output apk file')
 firmware = subparsers.add_parser('firmware', description='Update the firmware')
 firmware.add_argument('-f', dest='datFile', type=argparse.FileType('rb'), required=True, help='the firmware file')
 firmware.add_argument('-d', dest='driver', choices=drivers, help='specify the driver')
 updaterShell = subparsers.add_parser('updatershell', description='Launch firmware updater debug shell')
 updaterShell.add_argument('-d', dest='driver', choices=drivers, help='specify the driver')
 updaterShellMode = updaterShell.add_mutually_exclusive_group()
 updaterShellMode.add_argument('-f', dest='fdatFile', type=argparse.FileType('rb'), help='firmware file')
 updaterShellMode.add_argument('-m', dest='model', help='model name')
 guessFirmware = subparsers.add_parser('guess_firmware', description='Guess the applicable firmware file')
 guessFirmware.add_argument('-d', dest='driver', choices=drivers, help='specify the driver')
 guessFirmware.add_argument('-f', dest='file', type=argparse.FileType('rb'), required=True, help='input file')
 gps = subparsers.add_parser('gps', description='Update GPS assist data')
 gps.add_argument('-d', dest='driver', choices=drivers, help='specify the driver')
 gps.add_argument('-f', dest='file', type=argparse.FileType('rb'), help='assistme.dat file')
 stream = subparsers.add_parser('stream', description='Update Streaming configuration')
 stream.add_argument('-d', dest='driver', choices=drivers, help='specify the driver')
 stream.add_argument('-f', dest='file', type=argparse.FileType('w'), help='store current settings to file')
 stream.add_argument('-w', dest='write', type=argparse.FileType('r'), help='program camera settings from file')
 wifi = subparsers.add_parser('wifi', description='Update WiFi configuration')
 wifi.add_argument('-d', dest='driver', choices=drivers, help='specify the driver')
 wifi.add_argument('-m', dest='multi', action='store_true', help='Read/Write "Multi-WiFi" settings')
 wifi.add_argument('-f', dest='file', type=argparse.FileType('w'), help='store current settings to file')
 wifi.add_argument('-w', dest='write', type=argparse.FileType('r'), help='program camera settings from file')

 args = parser.parse_args()
 if args.command == 'info':
  infoCommand(args.driver)
 elif args.command == 'install':
  if args.appInteractive:
   pkg = appSelectionCommand()
   if not pkg:
    return
  else:
   pkg = args.appPackage
  installCommand(args.driver, args.apkFile, pkg, args.outFile, args.local)
 elif args.command == 'market':
  marketCommand(args.token)
 elif args.command == 'apk2spk':
  args.outFile.write(spk.dump(args.inFile.read()))
 elif args.command == 'spk2apk':
  args.outFile.write(spk.parse(args.inFile.read()))
 elif args.command == 'firmware':
  firmwareUpdateCommand(args.datFile, args.driver)
 elif args.command == 'updatershell':
  updaterShellCommand(args.model, args.fdatFile, args.driver)
 elif args.command == 'guess_firmware':
  guessFirmwareCommand(args.file, args.driver)
 elif args.command == 'gps':
  gpsUpdateCommand(args.file, args.driver)
 elif args.command == 'stream':
  streamingCommand(args.write, args.file, args.driver)
 elif args.command == 'wifi':
  wifiCommand(args.write, args.file, args.multi, args.driver)
 else:
  parser.print_usage()


if __name__ == '__main__':
 main()
