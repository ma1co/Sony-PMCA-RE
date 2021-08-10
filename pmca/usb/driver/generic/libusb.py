"""A wrapper to use libusb. Default on linux, on Windows you have to install a generic driver for your camera"""

import sys
import usb.core
import usb.util

from . import *

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
  super(MscContext, self).__init__('MSC', USB_CLASS_MSC, MscDriver)

class MtpContext(_UsbContext):
 def __init__(self):
  super(MtpContext, self).__init__('MTP', USB_CLASS_PTP, MtpDriver)

class VendorSpecificContext(_UsbContext):
 def __init__(self):
  super(VendorSpecificContext, self).__init__('vendor-specific', USB_CLASS_VENDOR_SPECIFIC, GenericUsbDriver)


def _listDevices(vendor, classType):
 """Lists all detected USB devices"""
 for dev in usb.core.find(find_all=True, idVendor=vendor):
  interface = next((interface for config in dev for interface in config), None)
  if interface and interface.bInterfaceClass == classType:
   yield UsbDeviceHandle(dev, dev.idVendor, dev.idProduct)


class UsbBackend(BaseUsbBackend):
 """Bulk reading and writing to USB devices"""

 def __init__(self, device):
  self.dev = device
  self.dev.default_timeout = 5000

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
  if sys.platform == 'darwin':
   self.dev.reset()

 def clearHalt(self, ep):
  self.dev.clear_halt(ep)

 def read(self, ep, length, timeout=None):
  try:
   return self.dev.read(ep, length, timeout).tobytes()
  except usb.core.USBError:
   raise GenericUsbException()

 def write(self, ep, data):
  try:
   self.dev.write(ep, data)
  except usb.core.USBError:
   raise GenericUsbException()

 def vendorRequestOut(self, request, value, index, data=b''):
  try:
   self.dev.ctrl_transfer(usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_OTHER, request, value, index, data)
  except usb.core.USBError as e:
   raise GenericUsbException()
