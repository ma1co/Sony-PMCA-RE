"""A wrapper to use libusb. Default on linux, on Windows you have to install a generic driver for your camera"""

import errno
import subprocess
import sys
import time

import usb.core
import usb.util

from . import *

# On macOS, prefer the libusb binary shipped inside the libusb-package wheel, so that
# no system-wide libusb installation (e.g. Homebrew) is required. Other platforms
# keep using the system libusb, as upstream does.
_backend = None
if sys.platform == 'darwin':
 try:
  import libusb_package
  _backend = libusb_package.get_libusb1_backend()
 except Exception:
  pass

# macOS daemons which grab PTP/MTP cameras as soon as they are plugged in.
# While one of them holds the camera, libusb cannot claim the interface.
_MACOS_CAMERA_DAEMONS = ['ptpcamerad', 'PTPCamera', 'ptpcamerad_sb', 'mscamerad']


class _UsbContext(BaseUsbContext):
 def __init__(self, name, classType, driverClass):
  super(_UsbContext, self).__init__('libusb-%s' % name, classType)
  self._driverClass = driverClass

 def listDevices(self, vendor):
  return _listDevices(vendor, self.classType)

 def openDevice(self, device):
  return self._driverClass(UsbBackend(device.handle))


class MscContext(_UsbContext):
 def __init__(self):
  super(MscContext, self).__init__('MSC', USB_CLASS_MSC, None)

 def openDevice(self, device):
  backend = UsbBackend(device.handle)
  interface = next((interface for config in device.handle for interface in config), None)
  if interface.bInterfaceProtocol in (0, 1):
   return MscCbiDriver(backend)
  elif interface.bInterfaceProtocol == 0x50:
   return MscBbbDriver(backend)
  else:
   raise Exception('Invalid protocol')

class MtpContext(_UsbContext):
 def __init__(self):
  super(MtpContext, self).__init__('MTP', USB_CLASS_PTP, MtpDriver)

class VendorSpecificContext(_UsbContext):
 def __init__(self):
  super(VendorSpecificContext, self).__init__('vendor-specific', USB_CLASS_VENDOR_SPECIFIC, GenericUsbDriver)


def _listDevices(vendor, classType):
 """Lists all detected USB devices"""
 for dev in usb.core.find(find_all=True, idVendor=vendor, backend=_backend):
  interface = next((interface for config in dev for interface in config), None)
  if interface and interface.bInterfaceClass == classType:
   yield UsbDeviceHandle(dev, dev.idVendor, dev.idProduct)


def _releaseMacosCamera():
 """Ask the macOS camera daemons to let go of the device. They are restarted automatically by launchd."""
 released = False
 for name in _MACOS_CAMERA_DAEMONS:
  try:
   if subprocess.call(['killall', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
    released = True
  except OSError:
   pass
 if released:
  time.sleep(1)
 return released


class UsbBackend(BaseUsbBackend):
 """Bulk reading and writing to USB devices"""

 def __init__(self, device):
  self.dev = device
  self.dev.default_timeout = 5000
  self._claimed = False

 def __del__(self):
  usb.util.dispose_resources(self.dev)

 def getId(self):
  return self.dev.idVendor, self.dev.idProduct

 def getEndpoints(self):
  return self.dev.get_active_configuration()[(0, 0)]

 def reset(self):
  try:
   if self.dev.is_kernel_driver_active(0):
    self.dev.detach_kernel_driver(0)
  except NotImplementedError:
   pass
  except usb.core.USBError:
   # On macOS a camera daemon holding the device surfaces here; _claim() deals with it
   if sys.platform != 'darwin':
    raise

 def _claim(self):
  """Claims the interface on macOS, working around daemons which hold the camera.
  Other platforms leave claiming to pyusb, as upstream does."""
  if self._claimed or sys.platform != 'darwin':
   return
  try:
   usb.util.claim_interface(self.dev, 0)
  except usb.core.USBError as e:
   if e.errno in (errno.EACCES, errno.EBUSY):
    print('macOS is holding the camera, trying to release it')
    if _releaseMacosCamera():
     try:
      usb.util.claim_interface(self.dev, 0)
     except usb.core.USBError:
      raise GenericUsbException('Cannot access the camera. Close Photos, Image Capture and any other application using the camera, then reconnect it.')
    else:
     raise GenericUsbException('Cannot access the camera. Close Photos, Image Capture and any other application using the camera, then reconnect it.')
   else:
    raise GenericUsbException('Cannot access the camera (%s)' % e)
  self._claimed = True

 def clearHalt(self, ep):
  self.dev.clear_halt(ep)

 def read(self, ep, length, timeout=None):
  self._claim()
  try:
   return self.dev.read(ep, length, timeout).tobytes()
  except usb.core.USBError:
   raise GenericUsbException()

 def write(self, ep, data):
  self._claim()
  try:
   self.dev.write(ep, data)
  except usb.core.USBError:
   raise GenericUsbException()

 def classInterfaceRequestOut(self, request, value, index, data=b''):
  self._claim()
  try:
   self.dev.ctrl_transfer(usb.util.CTRL_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE, request, value, index, data)
  except usb.core.USBError as e:
   raise GenericUsbException()

 def vendorRequestOut(self, request, value, index, data=b''):
  self._claim()
  try:
   self.dev.ctrl_transfer(usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_OTHER, request, value, index, data)
  except usb.core.USBError as e:
   raise GenericUsbException()
