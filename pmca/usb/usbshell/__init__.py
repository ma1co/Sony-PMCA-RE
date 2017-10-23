import binascii
import os
import posixpath
import time

from .interactive import *
from .transfer import *
from .. import *
from ...util import *

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


def _toCString(s, l):
 if len(s) + 1 > l:
  raise Exception('String too long')
 return s.ljust(l, b'\0')

def _openOutputFile(fn):
 if os.path.exists(fn):
  i = 1
  while os.path.exists(fn + ('-%d' % i)):
   i += 1
  fn += ('-%d' % i)
 return open(fn, 'wb')


def usbshell_loop(dev):
 transfer = UsbSequenceTransfer(dev, USB_FEATURE_SHELL)

 def req(cmd, data=b'', quiet=False):
  r = UsbShellResponse.unpack(transfer.exec(UsbShellRequest.pack(
   cmd = cmd,
   data = _toCString(data, 0xfff8),
  ), UsbShellResponse.size))
  if r.result & 0x80000000:
   if not quiet:
    print('Error')
   return r.result - 0x100000000
  else:
   return r.result

 for i in range(10):
  try:
   if req(b'TEST') == USB_RESULT_SUCCESS:
    break
  except InvalidCommandException:
   pass
  time.sleep(.5)
 else:
  raise Exception('Shell did not connect')

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
   keys = {
    b'MODL': 'Model',
    b'PROD': 'Product code',
    b'SERN': 'Serial number',
    b'BKRG': 'Backup region',
    b'FIRM': 'Firmware version',
   }
   for i in range(req(b'PROP')):
    prop = UsbListResponse.unpack(transfer.exec(b'', UsbListResponse.size))
    if prop.id in keys:
     print('%-20s%s' % (keys[prop.id] + ': ', prop.value.rstrip(b'\0').decode('latin1')))

  elif cmd == 'tweak':
   keys = {
    b'RECL': 'Disable video recording limit',
    b'RL4K': 'Disable 4K video recording limit',
    b'LANG': 'Unlock all languages',
    b'NTSC': 'Enable PAL / NTSC selector & warning',
    b'PROT': 'Unlock protected settings',
   }
   while True:
    tweaks = []
    for i in range(req(b'TLST')):
     tweak = UsbListResponse.unpack(transfer.exec(b'', UsbListResponse.size))
     if tweak.id in keys:
      tweaks.append(tweak)

    if not tweaks:
     print('No tweaks available')
     break

    for i, tweak in enumerate(tweaks):
     print('%d: [%s] %s' % (i+1, ('X' if tweak.status else ' '), keys[tweak.id]))
     value = tweak.value.rstrip(b'\0').decode('latin1')
     if value != '':
      print('       %s' % value)
     print()

    try:
     while True:
      try:
       i = int(input('Enter number of tweak to toggle (0 to finish): '))
       if 0 <= i <= len(tweaks):
        break
      except ValueError:
       pass
    except KeyboardInterrupt:
     print()
     break

    if i == 0:
     break
    else:
     tweak = tweaks[i - 1]
     res = req(b'TSET', UsbTweakRequest.pack(id=tweak.id, enable=not tweak.status), True)
     print({USB_RESULT_SUCCESS: 'Success', USB_RESULT_ERROR_PROTECTION: 'Error: Protection enabled'}.get(res, 'Error'))
     print()

  elif cmd == 'shell':
   if req(b'SHEL') == USB_RESULT_SUCCESS:
    usb_transfer_interactive_shell(transfer)

  elif cmd.startswith('shell '):
   if req(b'EXEC', cmd[len('shell '):].strip().encode('latin1')) == USB_RESULT_SUCCESS:
    usb_transfer_interactive_shell(transfer, stdin=False)

  elif cmd.startswith('pull '):
   fn = cmd[len('pull '):].strip()
   if req(b'PULL', fn.encode('latin1')) == USB_RESULT_SUCCESS:
    with _openOutputFile(posixpath.basename(fn)) as f:
     print('Writing to %s...' % f.name)
     usb_transfer_read(transfer, f)

  elif cmd == 'bootloader':
   for i in range(req(b'BLDR')):
    with _openOutputFile('boot%d' % (i + 1)) as f:
     print('Writing to %s...' % f.name)
     usb_transfer_read(transfer, f)

  elif cmd == 'exit':
   if req(b'EXIT') == USB_RESULT_SUCCESS:
    break

  elif cmd != '':
   print('Error: Unknown command')
