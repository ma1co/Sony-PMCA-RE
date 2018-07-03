"""A wrapper to use libusb. Default on linux, on Windows you have to install a generic driver for your camera"""

import sys
import usb.core
import usb.util

from . import *

class _UsbContext(object):
 def __init__(self, name, classType, driverClass):
  self.name = 'libusb-%s' % name
  self.classType = classType
  self._driverClass = driverClass

 def __enter__(self):
  return self

 def __exit__(self, *ex):
  pass

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


def _listDevices(vendor, classType):
 """Lists all detected USB devices"""
 for dev in usb.core.find(find_all=True, idVendor=vendor):
  interface = next((interface for config in dev for interface in config), None)
  if interface and interface.bInterfaceClass == classType:
   yield UsbDevice(dev, dev.idVendor, dev.idProduct)


class UsbBackend(object):
 """Bulk reading and writing to USB devices"""

 def __init__(self, device):
  self.dev = device

 def __del__(self):
  usb.util.dispose_resources(self.dev)

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

 def clear_halt(self, ep):
  self.dev.clear_halt(ep)

 def read(self, ep, length):
  try:
   return self.dev.read(ep, length).tostring()
  except usb.core.USBError:
   raise GenericUsbException()

 def write(self, ep, data):
  try:
   self.dev.write(ep, data)
  except usb.core.USBError:
   raise GenericUsbException()
