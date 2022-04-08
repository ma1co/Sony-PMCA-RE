"""A wrapper to use IOCTL_SCSI_PASS_THROUGH_DIRECT"""

from ctypes import *
from ctypes.wintypes import *
import string
from win32file import *

from . import *
from .setupapi import *
from .. import *

IOCTL_SCSI_PASS_THROUGH_DIRECT = 0x4d014
IOCTL_STORAGE_GET_DEVICE_NUMBER = 0x2d1080

SCSI_IOCTL_DATA_OUT = 0
SCSI_IOCTL_DATA_IN = 1
SCSI_IOCTL_DATA_UNSPECIFIED = 2

class SCSI_PASS_THROUGH_DIRECT(Structure):
 _fields_ = [
  ('Length', c_ushort),
  ('ScsiStatus', c_ubyte),
  ('PathId', c_ubyte),
  ('TargetId', c_ubyte),
  ('Lun', c_ubyte),
  ('CdbLength', c_ubyte),
  ('SenseInfoLength', c_ubyte),
  ('DataIn', c_ubyte),
  ('DataTransferLength', c_ulong),
  ('TimeOutValue', c_ulong),
  ('DataBuffer', c_void_p),
  ('SenseInfoOffset', c_ulong),
  ('Cdb', c_ubyte * 16),
 ]

class SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER(Structure):
 _fields_ = [
  ('sptd', SCSI_PASS_THROUGH_DIRECT),
  ('Filler', c_ulong),
  ('ucSenseBuf', c_ubyte * 32),
 ]

class STORAGE_DEVICE_NUMBER(Structure):
 _fields_ = [
  ('DeviceType', DWORD),
  ('DeviceNumber', ULONG),
  ('PartitionNumber', ULONG),
 ]


class MscContext(BaseUsbContext):
 def __init__(self):
  super(MscContext, self).__init__('Windows-MSC', USB_CLASS_MSC)

 def listDevices(self, vendor):
  return (dev for dev in _listDevices() if dev.idVendor == vendor)

 def openDevice(self, device):
  return _MscDriver(device.handle)


def _listLogicalDrives(type=DRIVE_REMOVABLE):
 mask = GetLogicalDrives()
 for i, l in enumerate(string.ascii_uppercase):
  if mask & (1 << i) and GetDriveType('%s:\\' % l) == type:
   yield '\\\\.\\%s:' % l

def _getStorageNumber(path):
 handle = CreateFile(path, 0, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
 deviceNumber = STORAGE_DEVICE_NUMBER()
 try:
  DeviceIoControl(handle, IOCTL_STORAGE_GET_DEVICE_NUMBER, None, deviceNumber)
  storageNumber = deviceNumber.DeviceType, deviceNumber.DeviceNumber
 except:
  storageNumber = None
 CloseHandle(handle)
 return storageNumber

def _listDevices():
 """Lists all detected mass storage devices"""
 # Similar to what calibre does: https://github.com/kovidgoyal/calibre/blob/master/src/calibre/devices/winusb.py
 logicalDrives = dict((_getStorageNumber(l), l) for l in _listLogicalDrives())
 disks = {dev: path for dev, (id, paths) in listDeviceClass(GUID_DEVINTERFACE_DISK) for path in paths}
 usbDevices = dict(listDeviceClass(GUID_DEVINTERFACE_USB_DEVICE))
 for usbInst, (usbPath, _) in usbDevices.items():
  for diskInst in listDeviceChildren(usbInst):
   if diskInst in disks:
    storageNumber = _getStorageNumber(disks[diskInst])
    if storageNumber and storageNumber in logicalDrives:
     idVendor, idProduct = parseDeviceId(usbPath)
     yield UsbDeviceHandle(logicalDrives[storageNumber], idVendor, idProduct)
     break# only return the first disk for every device


class _MscDriver(BaseMscDriver):
 """Communicate with a USB mass storage device"""
 def __init__(self, device):
  self.device = device

 def _sendScsiCommand(self, command, direction, data):
  sptd = SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER(sptd = SCSI_PASS_THROUGH_DIRECT(
   Length = sizeof(SCSI_PASS_THROUGH_DIRECT),
   DataIn = direction,
   DataTransferLength = sizeof(data) if data else 0,
   DataBuffer = cast(data, c_void_p),
   CdbLength = len(command),
   Cdb = (c_ubyte * 16).from_buffer_copy(command.ljust(16, b'\0')),
   TimeOutValue = 5,
   SenseInfoLength = SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER.ucSenseBuf.size,
   SenseInfoOffset = SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER.ucSenseBuf.offset,
  ))
  handle = CreateFile('\\\\.\\%s' % self.device, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
  result = DeviceIoControl(handle, IOCTL_SCSI_PASS_THROUGH_DIRECT, sptd, sizeof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER))
  CloseHandle(handle)
  if SCSI_PASS_THROUGH_DIRECT.from_buffer_copy(result).ScsiStatus != 0:
   sense = parseMscSense(result[SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER.ucSenseBuf.offset:])
   if sense == MSC_SENSE_OK:
    raise Exception('Mass storage error')
   return sense
  return MSC_SENSE_OK

 def sendCommand(self, command):
  return self._sendScsiCommand(command, SCSI_IOCTL_DATA_UNSPECIFIED, None)

 def sendWriteCommand(self, command, data):
  buffer = (c_ubyte * len(data)).from_buffer_copy(data)
  return self._sendScsiCommand(command, SCSI_IOCTL_DATA_OUT, buffer)

 def sendReadCommand(self, command, size):
  buffer = (c_ubyte * size)()
  status = self._sendScsiCommand(command, SCSI_IOCTL_DATA_IN, buffer)
  return status, bytes(bytearray(buffer))
