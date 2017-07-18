"""A wrapper to use IOCTL_SCSI_PASS_THROUGH_DIRECT"""

from comtypes import GUID
from ctypes import *
from ctypes.wintypes import *
import string
import sys
from win32file import *

from . import *
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

class SP_DEVICE_INTERFACE_DATA(Structure):
 _fields_ = [
  ('cbSize', DWORD),
  ('InterfaceClassGuid', GUID),
  ('Flags', DWORD),
  ('Reserved', POINTER(ULONG)),
 ]

class SP_DEVICE_INTERFACE_DETAIL_DATA(Structure):
 _pack_ = 4 if sys.maxsize > 2**32 else 2
 _fields_ = [
  ('cbSize', DWORD),
  ('DevicePath', WCHAR * 1),
 ]

class SP_DEVINFO_DATA(Structure):
 _fields_ = [
  ('cbSize', DWORD),
  ('ClassGuid', GUID),
  ('DevInst', DWORD),
  ('Reserved', POINTER(ULONG)),
 ]

class STORAGE_DEVICE_NUMBER(Structure):
 _fields_ = [
  ('DeviceType', DWORD),
  ('DeviceNumber', ULONG),
  ('PartitionNumber', ULONG),
 ]

SetupDiGetClassDevs = windll.setupapi.SetupDiGetClassDevsW
SetupDiGetClassDevs.restype = HANDLE
SetupDiGetClassDevs.argtypes = [POINTER(GUID), LPCWSTR, HWND, DWORD]

SetupDiDestroyDeviceInfoList = windll.setupapi.SetupDiDestroyDeviceInfoList
SetupDiDestroyDeviceInfoList.restype = BOOL
SetupDiDestroyDeviceInfoList.argtypes = [HANDLE]

SetupDiEnumDeviceInterfaces = windll.setupapi.SetupDiEnumDeviceInterfaces
SetupDiEnumDeviceInterfaces.restype = BOOL
SetupDiEnumDeviceInterfaces.argtypes = [HANDLE, c_void_p, POINTER(GUID), DWORD, POINTER(SP_DEVICE_INTERFACE_DATA)]

SetupDiGetDeviceInterfaceDetail = windll.setupapi.SetupDiGetDeviceInterfaceDetailW
SetupDiGetDeviceInterfaceDetail.restype = BOOL
SetupDiGetDeviceInterfaceDetail.argtypes = [HANDLE, POINTER(SP_DEVICE_INTERFACE_DATA), POINTER(SP_DEVICE_INTERFACE_DETAIL_DATA), DWORD, POINTER(DWORD), POINTER(SP_DEVINFO_DATA)]

CM_Get_Child = windll.CfgMgr32.CM_Get_Child
CM_Get_Child.restype = DWORD
CM_Get_Child.argtypes = [POINTER(DWORD), DWORD, ULONG]

CM_Get_Sibling = windll.CfgMgr32.CM_Get_Sibling
CM_Get_Sibling.restype = DWORD
CM_Get_Sibling.argtypes = [POINTER(DWORD), DWORD, ULONG]

GUID_DEVINTERFACE_USB_DEVICE = GUID('{A5DCBF10-6530-11D2-901F-00C04FB951ED}')
GUID_DEVINTERFACE_DISK = GUID('{53F56307-B6BF-11D0-94F2-00A0C91EFB8B}')
DIGCF_PRESENT = 2
DIGCF_DEVICEINTERFACE = 16


class MscContext(object):
 def __init__(self):
  self.name = 'Windows-MSC'
  self.classType = USB_CLASS_MSC

 def __enter__(self):
  return self

 def __exit__(self, *ex):
  pass

 def listDevices(self, vendor):
  return (dev for dev in _listDevices() if dev.idVendor == vendor)

 def openDevice(self, device):
  return _MscDriver(device.handle)


def _listDeviceClass(guid):
 handle = SetupDiGetClassDevs(byref(guid), None, None, DIGCF_DEVICEINTERFACE | DIGCF_PRESENT)
 if handle == INVALID_HANDLE_VALUE:
  raise Exception('SetupDiGetClassDevs failed')

 i = 0
 interfaceData = SP_DEVICE_INTERFACE_DATA()
 interfaceData.cbSize = sizeof(SP_DEVICE_INTERFACE_DATA)
 while SetupDiEnumDeviceInterfaces(handle, None, byref(guid), i, byref(interfaceData)):
  size = c_ulong(0)
  SetupDiGetDeviceInterfaceDetail(handle, byref(interfaceData), None, 0, byref(size), None)

  interfaceDetailData = SP_DEVICE_INTERFACE_DETAIL_DATA()
  interfaceDetailData.cbSize = sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA)
  resize(interfaceDetailData, size.value)
  devInfoData = SP_DEVINFO_DATA()
  devInfoData.cbSize = sizeof(SP_DEVINFO_DATA)
  if not SetupDiGetDeviceInterfaceDetail(handle, byref(interfaceData), byref(interfaceDetailData), size, None, byref(devInfoData)):
   raise Exception('SetupDiGetDeviceInterfaceDetail failed')

  yield devInfoData.DevInst, wstring_at(byref(interfaceDetailData, SP_DEVICE_INTERFACE_DETAIL_DATA.DevicePath.offset))
  i += 1

 if not SetupDiDestroyDeviceInfoList(handle):
  raise Exception('SetupDiDestroyDeviceInfoList failed')

def _listDeviceChildren(inst):
 child = DWORD(inst)
 f = CM_Get_Child
 while not f(byref(child), child, 0):
  yield child.value
  f = CM_Get_Sibling

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
 disks = dict(_listDeviceClass(GUID_DEVINTERFACE_DISK))
 usbDevices = dict(_listDeviceClass(GUID_DEVINTERFACE_USB_DEVICE))
 for usbInst, usbPath in usbDevices.items():
  for diskInst in _listDeviceChildren(usbInst):
   if diskInst in disks:
    storageNumber = _getStorageNumber(disks[diskInst])
    if storageNumber and storageNumber in logicalDrives:
     idVendor, idProduct = parseDeviceId(usbPath)
     yield UsbDevice(logicalDrives[storageNumber], idVendor, idProduct)
     break# only return the first disk for every device


class _MscDriver(object):
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
  return status, bytes(bytearray(buffer))
