import io
import time

from .transfer import *
from .. import *
from ....usb import *
from ....util import *

class UsbPlatformBackend(ShellPlatformBackend, FilePlatformBackend, MemoryPlatformBackend, BootloaderPlatformBackend, AndroidPlatformBackend, BackupPlatformBackend):
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

 UsbMemoryReadRequest = Struct('UsbMemoryReadRequest', [
  ('offset', Struct.INT32),
  ('size', Struct.INT32),
 ])

 UsbBackupReadRequest = Struct('UsbBackupReadRequest', [
  ('id', Struct.INT32),
 ])

 UsbBackupWriteRequest = Struct('UsbBackupWriteRequest', [
  ('id', Struct.INT32),
  ('size', Struct.INT32),
  ('data', Struct.STR % 0xfff4),
 ])

 UsbBackupDataRequest = Struct('UsbBackupDataRequest', [
  ('size', Struct.INT32),
 ])

 UsbBackupProtectionRequest = Struct('UsbBackupProtectionRequest', [
  ('enable', Struct.INT32),
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
   raise Exception(errorStrings.get(r.result - 0x100000000, 'Unknown error'))
  return r.result

 def start(self):
  for i in range(10):
   try:
    self._req(b'TEST')
    break
   except (InvalidCommandException, UnknownMscException):
    pass
   time.sleep(.5)
  else:
   raise Exception('Shell not connected')

 def interactiveShell(self, conn):
  self._req(b'SHEL')
  usb_transfer_socket(self.transfer, conn)

 def writeFile(self, path, f):
  self._req(b'PUSH', path.encode('latin1'))
  usb_transfer_write(self.transfer, f)

 def readFile(self, path, f, sizeCb=None):
  size = self._req(b'PULL', path.encode('latin1'))
  if sizeCb:
   sizeCb(size)
  usb_transfer_read(self.transfer, f)

 def readMemory(self, offset, size, f):
  self._req(b'RMEM', self.UsbMemoryReadRequest.pack(offset=offset, size=size))
  usb_transfer_read(self.transfer, f)

 def readBootloader(self):
  for i in range(self._req(b'BLDR')):
   f = io.BytesIO()
   usb_transfer_read(self.transfer, f)
   yield f.getvalue()

 def readBackup(self, id):
  size = self._req(b'BKRD', self.UsbBackupReadRequest.pack(id=id))
  return self.transfer.send(b'', size)

 def writeBackup(self, id, data):
  self._req(b'BKWR', self.UsbBackupWriteRequest.pack(id=id, size=len(data), data=data.ljust(0xfff4, b'\0')), {
   self.USB_RESULT_ERROR_PROTECTION: 'Protection enabled',
  })

 def syncBackup(self):
  self._req(b'BKSY')

 def getBackupStatus(self):
  size = self._req(b'BKST')
  return self.transfer.send(b'', size)

 def getBackupData(self):
  self._req(b'BKDA')
  f = io.BytesIO()
  usb_transfer_read(self.transfer, f)
  return f.getvalue()

 def setBackupData(self, data):
  self._req(b'BKDW', self.UsbBackupDataRequest.pack(size=len(data)))
  usb_transfer_write(self.transfer, io.BytesIO(data))

 def setBackupProtection(self, enable):
  self._req(b'BKPR', self.UsbBackupProtectionRequest.pack(enable=enable))

 def mountAndroidData(self):
  size = self._req(b'AMNT')
  return self.transfer.send(b'', size).decode('latin1')

 def unmountAndroidData(self, commitBackup):
  self._req(b'AUMT', self.UsbAndroidUnmountRequest.pack(commitBackup=commitBackup))

 def stop(self):
  self._req(b'EXIT')
