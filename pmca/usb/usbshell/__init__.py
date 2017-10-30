import os
import posixpath
import sys
import time

if sys.version_info < (3,):
 # Python 2
 input = raw_input

from .interactive import *
from .transfer import *
from .. import *
from ...util import *

class UsbShell:
 USB_FEATURE_SHELL = 0x23
 USB_RESULT_SUCCESS = 0
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

 def __init__(self, dev):
  self.transfer = UsbSequenceTransfer(dev, self.USB_FEATURE_SHELL)

 def _openOutputFile(self, fn):
  if os.path.exists(fn):
   i = 1
   while os.path.exists(fn + ('-%d' % i)):
    i += 1
   fn += ('-%d' % i)
  return open(fn, 'wb')

 def _req(self, cmd, data=b'', quiet=False):
  r = self.UsbShellResponse.unpack(self.transfer.send(self.UsbShellRequest.pack(
   cmd = cmd,
   data = data.ljust(0xfff8, b'\0'),
  ), self.UsbShellResponse.size))
  if r.result & 0x80000000:
   if not quiet:
    print('Error')
   return r.result - 0x100000000
  else:
   return r.result

 def waitReady(self):
  for i in range(10):
   try:
    if self._req(b'TEST') == self.USB_RESULT_SUCCESS:
     break
   except InvalidCommandException:
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
  errors = {
   self.USB_RESULT_SUCCESS: 'Success',
   self.USB_RESULT_ERROR_PROTECTION: 'Error: Protection enabled. Please disable protection first.'
  }
  res = self._req(b'TSET', self.UsbTweakRequest.pack(id=id, enable=enabled), True)
  print(errors.get(res, 'Error'))

 def startInteractiveShell(self):
  if self._req(b'SHEL') == self.USB_RESULT_SUCCESS:
   usb_transfer_interactive_shell(self.transfer)

 def execCommand(self, command):
  if self._req(b'EXEC', command.encode('latin1')) == self.USB_RESULT_SUCCESS:
   usb_transfer_interactive_shell(self.transfer, stdin=False)

 def pullFile(self, path):
  if self._req(b'PULL', path.encode('latin1')) == self.USB_RESULT_SUCCESS:
   with self._openOutputFile(posixpath.basename(path)) as f:
    print('Writing to %s...' % f.name)
    usb_transfer_read(self.transfer, f)

 def dumpBootloader(self):
  for i in range(self._req(b'BLDR')):
   with self._openOutputFile('boot%d' % (i + 1)) as f:
    print('Writing to %s...' % f.name)
    usb_transfer_read(self.transfer, f)

 def exit(self):
  self._req(b'EXIT')


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

  if cmd == 'help':
   print('List of supported commands:')
   for a, b in [
    ('help', 'Print this help message'),
    ('info', 'Print device info'),
    ('tweak', 'Tweak device settings'),
    ('shell', 'Start an interactive shell'),
    ('shell <COMMAND>', 'Execute the specified command'),
    ('pull <FILE>', 'Copy the specified file from the device to the computer'),
    ('bootloader', 'Dump the boot loader'),
    ('exit', 'Exit'),
   ]:
    print('%-16s %s' % (a, b))

  elif cmd == 'info':
   for id, desc, value in shell.getProperties():
    print('%-20s%s' % (desc + ': ', value))

  elif cmd == 'tweak':
   usbshell_tweak_loop(shell)

  elif cmd == 'shell':
   shell.startInteractiveShell()

  elif cmd.startswith('shell '):
   shell.execCommand(cmd[len('shell '):].strip())

  elif cmd.startswith('pull '):
   shell.pullFile(cmd[len('pull '):].strip())

  elif cmd == 'bootloader':
   shell.dumpBootloader()

  elif cmd == 'exit':
   shell.exit()
   break

  elif cmd != '':
   print('Error: Unknown command')


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
   id, desc, status, value = tweaks[i - 1]
   shell.setTweakEnabled(id, not status)
   print('')
