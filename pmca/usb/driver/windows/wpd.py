"""A wrapper to use the Windows Portable Device Api (WPD)"""

import comtypes
from comtypes import GUID
from comtypes.automation import *
from comtypes.client import *
from ctypes import *

from . import *
from .. import *

# Create and import the python comtypes wrapper for the needed DLLs
comtypes.client._generate.__verbose__ = False
_oldImport = comtypes.client._generate._my_import
def _newImport(fullname):
 try:
  import importlib
  importlib.invalidate_caches()
 except:
  # Python 2
  pass
 _oldImport(fullname)
comtypes.client._generate._my_import = _newImport

GetModule('PortableDeviceApi.dll')
GetModule('PortableDeviceTypes.dll')
from comtypes.gen.PortableDeviceApiLib import *
from comtypes.gen.PortableDeviceApiLib import _tagpropertykey as tpka
from comtypes.gen.PortableDeviceTypesLib import *


def propkey(fmtid, pid):
 key = _tagpropertykey()
 key.fmtid = GUID(fmtid)
 key.pid = pid
 return pointer(key)

wpdCommonGuid = '{F0422A9C-5DC8-4440-B5BD-5DF28835658A}'
wpdMtpGuid = '{4D545058-1A2E-4106-A357-771E0819FC56}'

WPD_PROPERTY_COMMON_COMMAND_CATEGORY = propkey(wpdCommonGuid, 1001)
WPD_PROPERTY_COMMON_COMMAND_ID = propkey(wpdCommonGuid, 1002)
WPD_PROPERTY_COMMON_HRESULT = propkey(wpdCommonGuid, 1003)

WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITHOUT_DATA_PHASE = propkey(wpdMtpGuid, 12)
WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ = propkey(wpdMtpGuid, 13)
WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_WRITE = propkey(wpdMtpGuid, 14)
WPD_COMMAND_MTP_EXT_READ_DATA = propkey(wpdMtpGuid, 15)
WPD_COMMAND_MTP_EXT_WRITE_DATA = propkey(wpdMtpGuid, 16)
WPD_COMMAND_MTP_EXT_END_DATA_TRANSFER = propkey(wpdMtpGuid, 17)

WPD_PROPERTY_MTP_EXT_OPERATION_CODE = propkey(wpdMtpGuid, 1001)
WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS = propkey(wpdMtpGuid, 1002)
WPD_PROPERTY_MTP_EXT_RESPONSE_CODE = propkey(wpdMtpGuid, 1003)
WPD_PROPERTY_MTP_EXT_TRANSFER_CONTEXT = propkey(wpdMtpGuid, 1006)
WPD_PROPERTY_MTP_EXT_TRANSFER_TOTAL_DATA_SIZE = propkey(wpdMtpGuid, 1007)
WPD_PROPERTY_MTP_EXT_TRANSFER_NUM_BYTES_TO_READ = propkey(wpdMtpGuid, 1008)
WPD_PROPERTY_MTP_EXT_TRANSFER_NUM_BYTES_TO_WRITE = propkey(wpdMtpGuid, 1010)
WPD_PROPERTY_MTP_EXT_TRANSFER_DATA = propkey(wpdMtpGuid, 1012)

class PROPVARIANT(Structure):
 _fields_ = [
  ('vt', c_ushort),
  ('reserved1', c_ubyte),
  ('reserved2', c_ubyte),
  ('reserved3', c_ulong),
  ('ulVal', c_ulong),
  ('reserved4', c_ulong),
 ]


class MtpContext(object):
 def __init__(self):
  self.name = 'Windows-MTP'
  self.classType = USB_CLASS_PTP

 def __enter__(self):
  comtypes.CoInitialize()
  return self

 def __exit__(self, *ex):
  comtypes.CoUninitialize()

 def listDevices(self, vendor):
  return (dev for dev in _listDevices() if dev.idVendor == vendor)

 def openDevice(self, device):
  return _MtpDriver(device.handle)


def _listDevices():
 """Lists all detected MTP devices"""
 # Create a device manager object
 pdm = CreateObject(PortableDeviceManager)

 length = c_ulong(0)
 pdm.GetDevices(POINTER(c_wchar_p)(), pointer(length))
 devices = (c_wchar_p * length.value)()
 pdm.GetDevices(devices, pointer(length))

 for id in devices:
  idVendor, idProduct = parseDeviceId(id)
  yield UsbDevice(id, idVendor, idProduct)

class _MtpDriver(object):
 """Send and receive MTP packages to a device."""
 def __init__(self, device):
  self.device = CreateObject(PortableDevice)
  self.device.Open(device, CreateObject(PortableDeviceValues))

 def _initCommandValues(self, command, context=None):
  params = CreateObject(PortableDeviceValues)
  params.SetGuidValue(WPD_PROPERTY_COMMON_COMMAND_CATEGORY, command.contents.fmtid)
  params.SetUnsignedIntegerValue(WPD_PROPERTY_COMMON_COMMAND_ID, command.contents.pid)
  if context:
   params.SetStringValue(WPD_PROPERTY_MTP_EXT_TRANSFER_CONTEXT, context)
  return params

 def _initPropCollection(self, values):
  params = CreateObject(PortableDevicePropVariantCollection)
  for value in values:
   p = PROPVARIANT()
   p.vt = VT_UI4
   p.ulVal = value
   params.Add(cast(pointer(p), POINTER(tag_inner_PROPVARIANT)))
  return params

 def _initInitialCommand(self, command, code, args):
  params = self._initCommandValues(command)
  params.SetUnsignedIntegerValue(WPD_PROPERTY_MTP_EXT_OPERATION_CODE, code)
  params.SetIPortableDevicePropVariantCollectionValue(WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS, self._initPropCollection(args))
  return params

 def _initDataCommand(self, command, context, lengthKey, data):
  params = self._initCommandValues(command, context)
  params.SetUnsignedLargeIntegerValue(lengthKey, len(data))
  params.SetBufferValue(WPD_PROPERTY_MTP_EXT_TRANSFER_DATA, (c_ubyte * len(data)).from_buffer_copy(data), len(data))
  return params

 def _send(self, params):
  result = self.device.SendCommand(0, params)
  code = result.GetErrorValue(cast(WPD_PROPERTY_COMMON_HRESULT, POINTER(tpka)))
  if code != 0:
   raise Exception('MTP SendCommand failed: 0x%x' % code)
  return result

 def _readResponse(self, context):
  params = self._initCommandValues(WPD_COMMAND_MTP_EXT_END_DATA_TRANSFER, context)
  result = self._send(params)
  return self._getResponse(result)

 def _getContext(self, result):
  return result.GetStringValue(cast(WPD_PROPERTY_MTP_EXT_TRANSFER_CONTEXT, POINTER(tpka)))

 def _getResponse(self, result):
  return result.GetUnsignedIntegerValue(cast(WPD_PROPERTY_MTP_EXT_RESPONSE_CODE, POINTER(tpka)))

 def reset(self):
  pass

 def sendCommand(self, code, args):
  """Send a PTP/MTP command without data phase"""
  params = self._initInitialCommand(WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITHOUT_DATA_PHASE, code, args)
  result = self._send(params)
  return self._getResponse(result)

 def sendWriteCommand(self, code, args, data):
  """Send a PTP/MTP command with write data phase"""
  params = self._initInitialCommand(WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_WRITE, code, args)
  params.SetUnsignedLargeIntegerValue(WPD_PROPERTY_MTP_EXT_TRANSFER_TOTAL_DATA_SIZE, len(data))
  result = self._send(params)
  context = self._getContext(result)

  params = self._initDataCommand(WPD_COMMAND_MTP_EXT_WRITE_DATA, context, WPD_PROPERTY_MTP_EXT_TRANSFER_NUM_BYTES_TO_WRITE, data)
  result = self._send(params)

  return self._readResponse(context)

 def sendReadCommand(self, code, args):
  """Send a PTP/MTP command with read data phase"""
  params = self._initInitialCommand(WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ, code, args)
  result = self._send(params)
  context = self._getContext(result)
  length = result.GetUnsignedIntegerValue(cast(WPD_PROPERTY_MTP_EXT_TRANSFER_TOTAL_DATA_SIZE, POINTER(tpka)))

  params = self._initDataCommand(WPD_COMMAND_MTP_EXT_READ_DATA, context, WPD_PROPERTY_MTP_EXT_TRANSFER_NUM_BYTES_TO_READ, b'\0'*length)
  result = self._send(params)
  data, length = result.GetBufferValue(cast(WPD_PROPERTY_MTP_EXT_TRANSFER_DATA, POINTER(tpka)))

  return self._readResponse(context), bytes(bytearray(data[:length]))
