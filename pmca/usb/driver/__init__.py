import abc
from collections import namedtuple

from ...util import *

USB_CLASS_PTP = 6
USB_CLASS_MSC = 8
USB_CLASS_VENDOR_SPECIFIC = 255

UsbDeviceHandle = namedtuple('UsbDeviceHandle', 'handle, idVendor, idProduct')

MSC_SENSE_OK = (0, 0, 0)
MSC_SENSE_ERROR_UNKNOWN = (0x2, 0xff, 0xff)

def parseMscSense(buffer):
 return parse8(buffer[2:3]) & 0xf, parse8(buffer[12:13]), parse8(buffer[13:14])


class BaseUsbDriver(object):
 def reset(self):
  pass


class BaseMscDriver(BaseUsbDriver, abc.ABC):
 @abc.abstractmethod
 def sendCommand(self, command):
  pass

 @abc.abstractmethod
 def sendWriteCommand(self, command, data):
  pass

 @abc.abstractmethod
 def sendReadCommand(self, command, size):
  pass


class BaseMtpDriver(BaseUsbDriver, abc.ABC):
 @abc.abstractmethod
 def sendCommand(self, code, args):
  pass

 @abc.abstractmethod
 def sendWriteCommand(self, code, args, data):
  pass

 @abc.abstractmethod
 def sendReadCommand(self, code, args):
  pass


class BaseUsbContext(abc.ABC):
 def __init__(self, name, classType):
  self.name = name
  self.classType = classType

 def __enter__(self):
  return self

 def __exit__(self, *ex):
  pass

 @abc.abstractmethod
 def listDevices(self, vendor):
  pass

 @abc.abstractmethod
 def openDevice(self, device):
  pass
