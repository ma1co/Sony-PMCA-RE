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

UsbShellRequest = Struct('UsbShellRequest', [
 ('cmd', Struct.STR % 4),
 ('data', Struct.STR % 0xfff8),
])

UsbShellResponse = Struct('UsbShellResponse', [
 ('result', Struct.INT32),
])

DeviceInfo = Struct('DeviceInfo', [
 ('model', Struct.STR % 16),
 ('product', Struct.STR % 5),
 ('serial', Struct.STR % 4),
 ('firmware', Struct.INT16),
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

 def req(cmd, data=b''):
  r = UsbShellResponse.unpack(transfer.exec(UsbShellRequest.pack(
   cmd = cmd,
   data = _toCString(data, 0xfff8),
  ), UsbShellResponse.size))
  if r.result & 0x80000000:
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
    ('shell', 'Start an interactive shell'),
    ('shell <COMMAND>', 'Execute the specified command'),
    ('pull <FILE>', 'Copy the specified file from the device to the computer'),
    ('bootloader', 'Dump the boot loader'),
    ('exit', 'Exit'),
   ]:
    print('%-16s %s' % (a, b))

  elif cmd == 'info':
   if req(b'INFO') == USB_RESULT_SUCCESS:
    info = DeviceInfo.unpack(transfer.exec(b'', DeviceInfo.size))
    for k, v in [
     ('Model', info.model.rstrip(b'\0').decode('latin1')),
     ('Product code', binascii.hexlify(info.product).decode('latin1')),
     ('Serial number', binascii.hexlify(info.serial).decode('latin1')),
     ('Firmware version', '%x.%02x' % ((info.firmware >> 8) & 0xff, info.firmware & 0xff)),
    ]:
     print('%-20s%s' % (k + ': ', v))

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
