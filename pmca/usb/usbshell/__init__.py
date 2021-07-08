import io
import os
import posixpath
import sys
import time

if sys.version_info < (3,):
 # Python 2
 input = raw_input

from .android import *
from .transfer import *
from .. import *
from ...io import *
from ...shell import *
from ...shell.interactive import *
from ...shell.parser import *
from ...util import *

class UsbShellException(Exception):
 pass

class UpdaterShellBackend:
 USB_FEATURE_SHELL = 0x23
 USB_RESULT_ERROR = -1
 USB_RESULT_ERROR_PROTECTION = -2

 UsbShellRequest = Struct('UsbShellRequest', [
  ('cmd', Struct.STR % 4),
  ('data', Struct.STR % 0xfff8),
 ])

 UsbShellResponse = Struct('UsbShellResponse', [
  ('result', Struct.INT32),
 ])

 UsbTweakRequest = Struct('UsbTweakRequest', [
  ('id', Struct.STR % 4),
  ('enable', Struct.INT32),
 ])

 UsbListResponse = Struct('UsbListResponse', [
  ('id', Struct.STR % 4),
  ('status', Struct.INT32),
  ('value', Struct.STR % 0xfff4),
 ])

 UsbBackupReadRequest = Struct('UsbBackupReadRequest', [
  ('id', Struct.INT32),
 ])

 UsbBackupWriteRequest = Struct('UsbBackupWriteRequest', [
  ('id', Struct.INT32),
  ('size', Struct.INT32),
  ('data', Struct.STR % 0xfff4),
 ])

 UsbAndroidUnmountRequest = Struct('UsbAndroidUnmountRequest', [
  ('commitBackup', Struct.INT32),
 ])

 def __init__(self, dev):
  self.transfer = UsbSequenceTransfer(dev, self.USB_FEATURE_SHELL)

 def _req(self, cmd, data=b'', errorStrings={}):
  r = self.UsbShellResponse.unpack(self.transfer.send(self.UsbShellRequest.pack(
   cmd = cmd,
   data = data.ljust(0xfff8, b'\0'),
  ), self.UsbShellResponse.size))
  if r.result & 0x80000000:
   raise UsbShellException(errorStrings.get(r.result - 0x100000000, 'Unknown error'))
  return r.result

 def waitReady(self):
  for i in range(10):
   try:
    self._req(b'TEST')
    break
   except (InvalidCommandException, UnknownMscException):
    pass
   time.sleep(.5)
  else:
   raise Exception('Shell not connected')

 def getProperties(self):
  keys = {
   b'MODL': 'Model',
   b'PROD': 'Product code',
   b'SERN': 'Serial number',
   b'BKRG': 'Backup region',
   b'FIRM': 'Firmware version',
  }
  for i in range(self._req(b'PROP')):
   prop = self.UsbListResponse.unpack(self.transfer.send(b'', self.UsbListResponse.size))
   if prop.id in keys:
    yield prop.id, keys[prop.id], prop.value.rstrip(b'\0').decode('latin1')

 def getTweakStatus(self):
  keys = {
   b'RECL': 'Disable video recording limit',
   b'RL4K': 'Disable 4K video recording limit',
   b'LANG': 'Unlock all languages',
   b'NTSC': 'Enable PAL / NTSC selector & warning',
   b'UAPP': 'Enable USB app installer',
   b'PROT': 'Unlock protected settings',
  }
  for i in range(self._req(b'TLST')):
   tweak = self.UsbListResponse.unpack(self.transfer.send(b'', self.UsbListResponse.size))
   if tweak.id in keys:
    value = tweak.value.rstrip(b'\0').decode('latin1')
    if value == '':
     value = 'Enabled' if tweak.status else 'Disabled'
    yield tweak.id, keys[tweak.id], tweak.status, value

 def setTweakEnabled(self, id, enabled):
  self._req(b'TSET', self.UsbTweakRequest.pack(id=id, enable=enabled), {
   self.USB_RESULT_ERROR_PROTECTION: 'Protection enabled. Please disable protection first.',
  })

 def startInteractiveShell(self):
  self._req(b'SHEL')
  return lambda conn: usb_transfer_socket(self.transfer, conn)

 def execCommand(self, command):
  self._req(b'EXEC', command.encode('latin1'))
  return lambda conn: usb_transfer_socket(self.transfer, conn)

 def readFile(self, path, f, sizeCb=None):
  size = self._req(b'PULL', path.encode('latin1'))
  if sizeCb:
   sizeCb(size)
  usb_transfer_read(self.transfer, f)

 def writeFile(self, path, f):
  self._req(b'PUSH', path.encode('latin1'))
  usb_transfer_write(self.transfer, f)

 def getFileSize(self, path):
  return self._req(b'STAT', path.encode('latin1'))

 def dumpBootloader(self):
  for i in range(self._req(b'BLDR')):
   f = io.BytesIO()
   usb_transfer_read(self.transfer, f)
   yield f.getvalue()

 def dumpBootRom(self, f):
  self._req(b'BROM')
  usb_transfer_read(self.transfer, f)

 def readBackup(self, id):
  size = self._req(b'BKRD', self.UsbBackupReadRequest.pack(id=id))
  return self.transfer.send(b'', size)

 def writeBackup(self, id, data):
  self._req(b'BKWR', self.UsbBackupWriteRequest.pack(id=id, size=len(data), data=data.ljust(0xfff4, b'\0')), {
   self.USB_RESULT_ERROR_PROTECTION: 'Protection enabled',
  })

 def syncBackup(self):
  self._req(b'BKSY')

 def mountAndroidData(self):
  size = self._req(b'AMNT')
  return self.transfer.send(b'', size).decode('latin1')

 def unmountAndroidData(self, commitBackup):
  self._req(b'AUMT', self.UsbAndroidUnmountRequest.pack(commitBackup=commitBackup))

 def exit(self):
  self._req(b'EXIT')


class UpdaterShell(Shell):
 def __init__(self, dev):
  super(UpdaterShell, self).__init__("USB debug shell")
  self.backend = UpdaterShellBackend(dev)

  self.addCommand('info', Command(self.info, (), 'Print device info'))
  self.addCommand('tweak', Command(self.tweak, (), 'Tweak device settings'))
  self.addCommand('shell', ResidueCommand(self.shell, 0, 'Start an interactive shell', '[<COMMAND>]'))
  self.addCommand('push', Command(self.push, (2,), 'Copy the specified file from the computer to the device', '<LOCAL> <REMOTE>'))
  self.addCommand('pull', Command(self.pull, (1, 1, ['.']), 'Copy the specified file from the device to the computer', '<REMOTE> [<LOCAL>]'))
  self.addCommand('bootloader', Command(self.bootloader, (0, 1, ['.']), 'Dump the boot loader', '[<OUTDIR>]'))
  self.addCommand('bootrom', Command(self.bootrom, (0, 1, ['.']), 'Dump the boot rom', '[<OUTDIR>]'))
  self.addCommand('install', Command(self.install, (1,), 'Install the specified android app', '<APKFILE>'))

  bk = SubCommand()
  bk.addCommand('r', Command(self.readBackup, (1,), 'Read backup property', '<ID>'))
  bk.addCommand('w', ResidueCommand(self.writeBackup, 1, 'Write backup property', '<ID> <DATA>'))
  bk.addCommand('s', Command(self.syncBackup, (), 'Sync backup data to disk'))
  self.addCommand('bk', bk)

 def run(self):
  self.backend.waitReady()
  super(UpdaterShell, self).run()
  self.backend.exit()

 def _openOutputFile(self, fn):
  if os.path.exists(fn):
   i = 1
   while os.path.exists(fn + ('-%d' % i)):
    i += 1
   fn += ('-%d' % i)
  return open(fn, 'wb')

 def info(self):
  for id, desc, value in self.backend.getProperties():
   print('%-20s%s' % (desc + ': ', value))

 def shell(self, cmd=''):
  if cmd != '':
   run_interactive_shell(self.backend.execCommand(cmd), stdin=False)
  else:
   run_interactive_shell(self.backend.startInteractiveShell())

 def push(self, localPath, path):
  with open(localPath, 'rb') as f:
   print('Writing to %s...' % path)
   self.backend.writeFile(path, ProgressFile(f))

 def pull(self, path, localPath='.'):
  if os.path.isdir(localPath):
   localPath = os.path.join(localPath, posixpath.basename(path))
  with self._openOutputFile(localPath) as f:
   print('Writing to %s...' % f.name)
   p = ProgressFile(f)
   self.backend.readFile(path, p, p.setTotal)

 def bootloader(self, localPath='.'):
  if not os.path.isdir(localPath):
   raise Exception('%s is not a directory' % localPath)
  for i, data in enumerate(self.backend.dumpBootloader()):
   with self._openOutputFile(os.path.join(localPath, 'boot%d' % (i + 1))) as f:
    print('Writing to %s...' % f.name)
    f.write(data)

 def bootrom(self, localPath='.'):
  if os.path.isdir(localPath):
   localPath = os.path.join(localPath, 'bootrom')
  with self._openOutputFile(localPath) as f:
   print('Writing to %s...' % f.name)
   self.backend.dumpBootRom(f)

 def readBackup(self, id):
  id = int(id, 16)
  value = self.backend.readBackup(id)
  print(' '.join('%02x' % ord(value[i:i+1]) for i in range(len(value))))

 def writeBackup(self, id, data):
  id = int(id, 16)
  value = []
  parser = ArgParser(data)
  if not parser.available():
   raise ValueError('Not enough arguments provided')
  while parser.available():
   value.append(int(parser.consumeRequiredArg(), 16))
  self.backend.writeBackup(id, bytes(bytearray(value)))
  print('Success')

 def syncBackup(self):
  self.backend.syncBackup()

 def install(self, apkFile):
  with open(apkFile, 'rb') as f:
   installApk(self.backend, f)

 def exit(self):
  try:
   self.backend.syncBackup()
  except:
   print('Cannot sync backup')
  super(UpdaterShell, self).exit()

 def tweak(self):
  while True:
   tweaks = list(self.backend.getTweakStatus())
   if not tweaks:
    print('No tweaks available')
    break

   for i, (id, desc, status, value) in enumerate(tweaks):
    print('%d: [%s] %s' % (i + 1, ('X' if status else ' '), desc))
    print('       %s' % value)
    print('')

   try:
    while True:
     try:
      i = int(input('Enter number of tweak to toggle (0 to finish): '))
      if 0 <= i <= len(tweaks):
       break
     except ValueError:
      pass
   except KeyboardInterrupt:
    print('')
    break

   if i == 0:
    break
   else:
    try:
     id, desc, status, value = tweaks[i - 1]
     self.backend.setTweakEnabled(id, not status)
     print('Success')
    except Exception as e:
     print('Error: %s' % e)
    print('')
