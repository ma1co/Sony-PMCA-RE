from . import *
from .setupapi import *
from .. import *

class VendorSpecificContext(BaseUsbContext):
 def __init__(self):
  super(VendorSpecificContext, self).__init__('Windows-vendor-specific', USB_CLASS_VENDOR_SPECIFIC)

 def listDevices(self, vendor):
  return (dev for dev in _listDevices() if dev.idVendor == vendor)

 def openDevice(self, device):
  return UnimplementedUsbDriver()

def _listDevices():
 for dev, (usbPath, _) in listDeviceClass(enumerator='USB', service=''):
  idVendor, idProduct = parseDeviceId(usbPath)
  yield UsbDeviceHandle(None, idVendor, idProduct)

class UnimplementedUsbDriver(BaseUsbDriver):
 pass
