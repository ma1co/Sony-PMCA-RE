"""A wrapper to use IOCTL_SCSI_PASS_THROUGH_DIRECT"""

from comtypes.client import *
from ctypes import *
from win32file import *

from . import *
from .. import *

IOCTL_SCSI_PASS_THROUGH_DIRECT = 0x4d014

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


def listDevices():
 """Lists all detected mass storage devices"""
 # Connect to a WMI object
 wmi = CoGetObject('winmgmts:')

 def getUsbDrivesFromSerial(serial):
  for disk in wmi.InstancesOf('Win32_DiskDrive'):
   if disk.Properties_['InterfaceType'].Value == 'USB' and disk.Properties_['SerialNumber'].Value == serial:
    for partition in wmi.AssociatorsOf(disk.Path_.Path, '', 'Win32_DiskPartition'):
     for logicalDisk in wmi.AssociatorsOf(partition.Path_.Path, '', 'Win32_LogicalDisk'):
      yield logicalDisk

 for hub in wmi.InstancesOf('Win32_USBHub'):
  deviceId = hub.Properties_['DeviceID'].Value
  idVendor, idProduct = parseDeviceId(deviceId)
  serial = deviceId.rpartition('\\')[2]
  drive = next(getUsbDrivesFromSerial(serial), None)
  if drive:
   yield UsbDevice(drive.Properties_['DeviceID'].Value, idVendor, idProduct, USB_CLASS_MSC)


class MscDriver:
 """Communicate with a USB mass storage device"""
 def __init__(self, device):
  self.device = device.handle

 def _sendScsiCommand(self, command, direction, data):
  sptd = SCSI_PASS_THROUGH_DIRECT(
   Length = sizeof(SCSI_PASS_THROUGH_DIRECT),
   DataIn = direction,
   DataTransferLength = sizeof(data) if data else 0,
   DataBuffer = cast(data, c_void_p),
   CdbLength = len(command),
   Cdb = (c_ubyte * 16).from_buffer_copy(command.ljust(16, '\x00')),
   TimeOutValue = 5,
  )
  handle = CreateFile('\\\\.\\%s' % self.device, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
  DeviceIoControl(handle, IOCTL_SCSI_PASS_THROUGH_DIRECT, sptd, sptd)
  CloseHandle(handle)
  return sptd.ScsiStatus

 def reset(self):
  pass

 def sendCommand(self, command):
  return self._sendScsiCommand(command, SCSI_IOCTL_DATA_UNSPECIFIED, None)

 def sendWriteCommand(self, command, data):
  buffer = (c_ubyte * len(data)).from_buffer_copy(data)
  return self._sendScsiCommand(command, SCSI_IOCTL_DATA_OUT, buffer)

 def sendReadCommand(self, command, size):
  buffer = (c_ubyte * size)()
  status = self._sendScsiCommand(command, SCSI_IOCTL_DATA_IN, buffer)
  return status, str(bytearray(buffer))
