from comtypes import GUID
from ctypes import *
from ctypes.wintypes import *
import sys

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

SetupDiGetClassDevs = windll.setupapi.SetupDiGetClassDevsW
SetupDiGetClassDevs.restype = HANDLE
SetupDiGetClassDevs.argtypes = [POINTER(GUID), LPCWSTR, HWND, DWORD]

SetupDiDestroyDeviceInfoList = windll.setupapi.SetupDiDestroyDeviceInfoList
SetupDiDestroyDeviceInfoList.restype = BOOL
SetupDiDestroyDeviceInfoList.argtypes = [HANDLE]

SetupDiEnumDeviceInfo = windll.setupapi.SetupDiEnumDeviceInfo
SetupDiEnumDeviceInfo.restype = BOOL
SetupDiEnumDeviceInfo.argtypes = [HANDLE, DWORD, POINTER(SP_DEVINFO_DATA)]

SetupDiEnumDeviceInterfaces = windll.setupapi.SetupDiEnumDeviceInterfaces
SetupDiEnumDeviceInterfaces.restype = BOOL
SetupDiEnumDeviceInterfaces.argtypes = [HANDLE, c_void_p, POINTER(GUID), DWORD, POINTER(SP_DEVICE_INTERFACE_DATA)]

SetupDiGetDeviceInterfaceDetail = windll.setupapi.SetupDiGetDeviceInterfaceDetailW
SetupDiGetDeviceInterfaceDetail.restype = BOOL
SetupDiGetDeviceInterfaceDetail.argtypes = [HANDLE, POINTER(SP_DEVICE_INTERFACE_DATA), POINTER(SP_DEVICE_INTERFACE_DETAIL_DATA), DWORD, POINTER(DWORD), POINTER(SP_DEVINFO_DATA)]

SetupDiGetDeviceRegistryProperty = windll.setupapi.SetupDiGetDeviceRegistryPropertyW
SetupDiGetDeviceRegistryProperty.restype = BOOL
SetupDiGetDeviceRegistryProperty.argtypes = [HANDLE, POINTER(SP_DEVINFO_DATA), DWORD, PDWORD, LPCWSTR, DWORD, PDWORD]

CM_Get_Child = windll.CfgMgr32.CM_Get_Child
CM_Get_Child.restype = DWORD
CM_Get_Child.argtypes = [POINTER(DWORD), DWORD, ULONG]

CM_Get_Sibling = windll.CfgMgr32.CM_Get_Sibling
CM_Get_Sibling.restype = DWORD
CM_Get_Sibling.argtypes = [POINTER(DWORD), DWORD, ULONG]

GUID_DEVINTERFACE_USB_DEVICE = GUID('{A5DCBF10-6530-11D2-901F-00C04FB951ED}')
GUID_DEVINTERFACE_DISK = GUID('{53F56307-B6BF-11D0-94F2-00A0C91EFB8B}')
DIGCF_PRESENT = 2
DIGCF_ALLCLASSES = 4
DIGCF_DEVICEINTERFACE = 16
SPDRP_HARDWAREID = 1
SPDRP_SERVICE = 4

INVALID_HANDLE_VALUE = 0x100 ** sizeof(HANDLE) - 1

def _getDeviceProperty(handle, devInfoData, prop):
 buf = create_unicode_buffer(512)
 if not SetupDiGetDeviceRegistryProperty(handle, byref(devInfoData), prop, None, buf, len(buf), None):
  return ''
 return buf.value

def _listDeviceInterfaces(handle, devInfoData, guid):
 i = 0
 interfaceData = SP_DEVICE_INTERFACE_DATA()
 interfaceData.cbSize = sizeof(SP_DEVICE_INTERFACE_DATA)
 while SetupDiEnumDeviceInterfaces(handle, byref(devInfoData), guid, i, byref(interfaceData)):
  size = c_ulong(0)
  SetupDiGetDeviceInterfaceDetail(handle, byref(interfaceData), None, 0, byref(size), None)

  interfaceDetailData = SP_DEVICE_INTERFACE_DETAIL_DATA()
  interfaceDetailData.cbSize = sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA)
  resize(interfaceDetailData, size.value)
  if not SetupDiGetDeviceInterfaceDetail(handle, byref(interfaceData), byref(interfaceDetailData), size, None, None):
   raise Exception('SetupDiGetDeviceInterfaceDetail failed')

  yield wstring_at(byref(interfaceDetailData, SP_DEVICE_INTERFACE_DETAIL_DATA.DevicePath.offset))
  i += 1

def listDeviceClass(guid=None, enumerator=None, service=None):
 handle = SetupDiGetClassDevs(guid, enumerator, None, DIGCF_PRESENT | (DIGCF_ALLCLASSES if not guid else 0) | (DIGCF_DEVICEINTERFACE if not enumerator else 0))
 if handle == INVALID_HANDLE_VALUE:
  raise Exception('SetupDiGetClassDevs failed')

 devInfoData = SP_DEVINFO_DATA()
 devInfoData.cbSize = sizeof(SP_DEVINFO_DATA)
 i = 0
 while SetupDiEnumDeviceInfo(handle, i, byref(devInfoData)):
  if service is None or _getDeviceProperty(handle, devInfoData, SPDRP_SERVICE) == service:
   yield devInfoData.DevInst, (_getDeviceProperty(handle, devInfoData, SPDRP_HARDWAREID), list(_listDeviceInterfaces(handle, devInfoData, guid)) if guid else [])
  i += 1

 if not SetupDiDestroyDeviceInfoList(handle):
  raise Exception('SetupDiDestroyDeviceInfoList failed')

def listDeviceChildren(inst):
 child = DWORD(inst)
 f = CM_Get_Child
 while not f(byref(child), child, 0):
  yield child.value
  f = CM_Get_Sibling
