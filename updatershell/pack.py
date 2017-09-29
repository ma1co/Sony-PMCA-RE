#!/usr/bin/env python3
import io
import os
from stat import *
import sys
import yaml

try:
 import fwtool
except ModuleNotFoundError:
 print('fwtool has to be in PYTHONPATH')
 sys.exit(1)
fwtoolPath = os.path.dirname(os.path.dirname(fwtool.__file__))

from fwtool.archive import cramfs, UnixFile
from fwtool.sony import fdat

def mkdirs(path):
 try:
  os.makedirs(path)
 except OSError:
  pass

bodyFiles = {
  0: 'libupdaterbody_gen1.so',
  1: 'libupdaterbody_gen1.so',
  2: 'libupdaterbody_gen2.so',
  3: 'libupdaterbody_gen3.so',
 }

if __name__ == '__main__':
 if len(sys.argv) != 3:
  print('Usage: pack.py buildDir fdatDir')
  sys.exit(1)
 buildDir = sys.argv[1]
 fdatDir = sys.argv[2]

 with open(fwtoolPath + '/devices.yml', 'r') as f:
  devices = yaml.safe_load(f)

 dataDict = {}
 for name, config in devices.items():
  fsFile = io.BytesIO()
  with open(buildDir + '/' + bodyFiles[config['gen']], 'rb') as f:
   cramfs.writeCramfs([UnixFile(
    path = '/bodylib/libupdaterbody.so',
    size = -1,
    mtime = 0,
    mode = S_IFREG | 0o775,
    uid = 0,
    gid = 0,
    contents = f,
   )], fsFile)

  fdatFile = io.BytesIO()
  fdat.writeFdat(fdat.FdatFile(
   model = config['model'],
   region = config['region'] if 'region' in config else 0,
   version = '9.99',
   isAccessory = False,
   firmware = io.BytesIO(),
   fs = fsFile,
  ), fdatFile)

  data = fdat.encryptFdat(fdatFile, 'gen%d' % config['gen']).read()
  dataDict.setdefault(config['gen'], {})[name] = data

 mkdirs(fdatDir)

 headerSize = 0x30
 for gen, datas in dataDict.items():
  payload = None
  for name, data in datas.items():
   if payload is None:
    payload = data[headerSize:]
   elif len(data) != headerSize + len(payload) or data[headerSize:] != payload:
    raise Exception('Cannot split header')

  with open(fdatDir + '/gen%d.dat' % gen, 'wb') as f:
   f.write(payload)

  mkdirs(fdatDir + '/gen%d' % gen)
  for name, data in datas.items():
   with open(fdatDir + '/gen%d/%s.hdr' % (gen, name), 'wb') as f:
    f.write(data[:headerSize])
