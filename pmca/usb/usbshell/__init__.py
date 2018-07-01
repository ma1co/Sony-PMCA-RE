import io
import os
import posixpath
import sys
import time

if sys.version_info < (3,):
 # Python 2
 input = raw_input

from .android import *
from .interactive import *
from .parser import *
from .transfer import *
from .. import *
from ...util import *

class UsbShellException(Exception):
 pass

class UsbShell:
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

 def _openOutputFile(self, fn):
  if os.path.exists(fn):
   i = 1
   while os.path.exists(fn + ('-%d' % i)):
    i += 1
   fn += ('-%d' % i)
  return open(fn, 'wb')

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
  usb_transfer_interactive_shell(self.transfer)

 def execCommand(self, command):
  self._req(b'EXEC', command.encode('latin1'))
  usb_transfer_interactive_shell(self.transfer, stdin=False)

 def readFile(self, path):
  self._req(b'PULL', path.encode('latin1'))
  f = io.BytesIO()
  usb_transfer_read(self.transfer, f)
  return f.getvalue()

 def writeFile(self, path, data):
  self._req(b'PUSH', path.encode('latin1'))
  usb_transfer_write(self.transfer, io.BytesIO(data))

 def getFileSize(self, path):
  return self._req(b'STAT', path.encode('latin1'))

 def pushFile(self, localPath, path):
  with open(localPath, 'rb') as f:
   try:
    self._req(b'PUSH', path.encode('latin1'))
   except UsbShellException:
    path = posixpath.join(path, os.path.basename(localPath))
    self._req(b'PUSH', path.encode('latin1'))
   print('Writing to %s...' % path)
   usb_transfer_write(self.transfer, f, os.fstat(f.fileno()).st_size, ProgressPrinter().cb)

 def pullFile(self, path, localPath='.'):
  if os.path.isdir(localPath):
   localPath = os.path.join(localPath, posixpath.basename(path))
  with self._openOutputFile(localPath) as f:
   size = self._req(b'PULL', path.encode('latin1'))
   print('Writing to %s...' % f.name)
   usb_transfer_read(self.transfer, f, size, ProgressPrinter().cb)

 def dumpBootloader(self, localPath='.'):
  if not os.path.isdir(localPath):
   raise Exception('%s is not a directory' % localPath)
  for i in range(self._req(b'BLDR')):
   with self._openOutputFile(os.path.join(localPath, 'boot%d' % (i + 1))) as f:
    print('Writing to %s...' % f.name)
    usb_transfer_read(self.transfer, f)

 def dumpBootRom(self, localPath='.'):
  if os.path.isdir(localPath):
   localPath = os.path.join(localPath, 'bootrom')
  size = self._req(b'BROM')
  with self._openOutputFile(localPath) as f:
   usb_transfer_read(self.transfer, f, size)

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


class ProgressPrinter:
 def __init__(self):
  self._percent = -1

 def cb(self, written, total):
  p = int(written * 20 / total) * 5 if total > 0 else 100
  if p != self._percent:
   print('%d%%' % p)
   self._percent = p


def usbshell_loop(dev):
 shell = UsbShell(dev)
 shell.waitReady()

 print('Welcome to the USB debug shell.')
 print('Type `help` for the list of supported commands.')
 print('Type `exit` to quit.')

 while True:
  try:
   cmd = input('>').strip()
  except KeyboardInterrupt:
   print('')
   continue

  try:
   parser = ArgParser(cmd)
   if not parser.available():
    continue
   cmd = parser.consumeRequiredArg()

   if cmd == 'help':
    parser.consumeArgs()
    print('List of supported commands:')
    for a, b in [
     ('help', 'Print this help message'),
     ('info', 'Print device info'),
     ('tweak', 'Tweak device settings'),
     ('shell', 'Start an interactive shell'),
     ('shell <COMMAND>', 'Execute the specified command'),
     ('push <LOCAL> <REMOTE>', 'Copy the specified file from the computer to the device'),
     ('pull <REMOTE> [<LOCAL>]', 'Copy the specified file from the device to the computer'),
     ('bootloader [<OUTDIR>]', 'Dump the boot loader'),
     ('bk r <ID>', 'Read backup property'),
     ('bk w <ID> <DATA>', 'Write backup property'),
     ('bk s', 'Sync backup data to disk'),
     ('install <APKFILE>', 'Install the specified android app'),
     ('exit', 'Exit'),
    ]:
     print('%-24s %s' % (a, b))

   elif cmd == 'info':
    parser.consumeArgs()
    for id, desc, value in shell.getProperties():
     print('%-20s%s' % (desc + ': ', value))

   elif cmd == 'tweak':
    parser.consumeArgs()
    usbshell_tweak_loop(shell)

   elif cmd == 'shell':
    if parser.available():
     shell.execCommand(parser.getResidue())
    else:
     shell.startInteractiveShell()

   elif cmd == 'push':
    shell.pushFile(*parser.consumeArgs(2))

   elif cmd == 'pull':
    shell.pullFile(*parser.consumeArgs(1, 1, ['.']))

   elif cmd == 'bootloader':
    shell.dumpBootloader(*parser.consumeArgs(0, 1, ['.']))

   elif cmd == 'bootrom':
    shell.dumpBootRom(*parser.consumeArgs(0, 1, ['.']))

   elif cmd == 'bk':
    subcmd = parser.consumeRequiredArg()

    if subcmd == 'r':
     id = int(parser.consumeRequiredArg(), 16)
     parser.consumeArgs()
     value = shell.readBackup(id)
     print(' '.join('%02x' % ord(value[i:i+1]) for i in range(len(value))))

    elif subcmd == 'w':
     id = int(parser.consumeRequiredArg(), 16)
     value = []
     if not parser.available():
      raise ValueError('Not enough arguments provided')
     while parser.available():
      value.append(int(parser.consumeRequiredArg(), 16))
     shell.writeBackup(id, bytes(bytearray(value)))
     print('Success')

    elif subcmd == 's':
     parser.consumeArgs()
     shell.syncBackup()

    else:
     raise Exception('Unknown subcommand')

   elif cmd == 'install':
    with open(parser.consumeArgs(1)[0], 'rb') as f:
     installApk(shell, f)

   elif cmd == 'exit':
    parser.consumeArgs()
    try:
     shell.syncBackup()
    except:
     print('Cannot sync backup')
    shell.exit()
    break

   else:
    raise Exception('Unknown command')

  except Exception as e:
   print('Error: %s' % e)


def usbshell_tweak_loop(shell):
 while True:
  tweaks = list(shell.getTweakStatus())
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
    shell.setTweakEnabled(id, not status)
    print('Success')
   except Exception as e:
    print('Error: %s' % e)
   print('')
