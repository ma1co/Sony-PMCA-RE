#!/usr/bin/env python
"""A command line application to install apps on Android-enabled Sony cameras"""
import argparse

import config
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
 subparsers = parser.add_subparsers(dest='command', title='commands')
 info = subparsers.add_parser('info', description='Display information about the camera connected via USB')
 info.add_argument('-d', dest='driver', choices=['libusb', 'windows'], help='specify the driver')
 install = subparsers.add_parser('install', description='Installs an apk file on the camera connected via USB. The connection can be tested without specifying a file.')
 install.add_argument('-s', dest='server', help='hostname for the remote server (set to empty to start a local server)', default=config.appengineServer)
 install.add_argument('-d', dest='driver', choices=['libusb', 'windows'], help='specify the driver')
 install.add_argument('-o', dest='outFile', type=argparse.FileType('w'), help='write the output to this file')
 install.add_argument('-f', dest='apkFile', type=argparse.FileType('rb'), help='the apk file to install')
 market = subparsers.add_parser('market', description='Download apps from the official Sony app store')
 market.add_argument('-t', dest='token', help='Specify an auth token')
 apk2spk = subparsers.add_parser('apk2spk', description='Convert apk to spk')
 apk2spk.add_argument('inFile', metavar='app.apk', type=argparse.FileType('rb'), help='the apk file to convert')
 apk2spk.add_argument('outFile', metavar='app' + spk.constants.extension, type=argparse.FileType('wb'), help='the output spk file')
 spk2apk = subparsers.add_parser('spk2apk', description='Convert spk to apk')
 spk2apk.add_argument('inFile', metavar='app' + spk.constants.extension, type=argparse.FileType('rb'), help='the spk file to convert')
 spk2apk.add_argument('outFile', metavar='app.apk', type=argparse.FileType('wb'), help='the output apk file')

 args = parser.parse_args()
 if args.command == 'info':
  infoCommand(config.appengineServer, args.driver)
 elif args.command == 'install':
  installCommand(args.server, args.driver, args.apkFile, args.outFile)
 elif args.command == 'market':
  marketCommand(args.token)
 elif args.command == 'apk2spk':
  args.outFile.write(spk.dump(args.inFile.read()))
 elif args.command == 'spk2apk':
  args.outFile.write(spk.parse(args.inFile.read()))


if __name__ == '__main__':
 main()
