"""A wrapper to use libusb. Default on linux, on Windows you have to install a generic driver for your camera"""

import usb.core

from . import *
from ...util import *

def listDevices():
 """Lists all detected USB devices"""
 for dev in usb.core.find(find_all=True):
  interface = dev.get_active_configuration().interfaces()[0]
  yield UsbDevice(dev, dev.idVendor, dev.idProduct, interface.bInterfaceClass)


class UsbDriver:
 """Bulk reading and writing to USB devices"""
 USB_ENDPOINT_TYPE_BULK = 2
 USB_ENDPOINT_MASK = 1
 USB_ENDPOINT_OUT = 0
 USB_ENDPOINT_IN = 1

 def __init__(self, device):
  self.dev = device.handle
  self.epIn = self._findEndpoint(self.USB_ENDPOINT_TYPE_BULK, self.USB_ENDPOINT_IN)
  self.epOut = self._findEndpoint(self.USB_ENDPOINT_TYPE_BULK, self.USB_ENDPOINT_OUT)

 def _findEndpoint(self, type, direction):
  interface = self.dev.get_active_configuration().interfaces()[0]
  for ep in interface:
   if ep.bmAttributes == type and ep.bEndpointAddress & self.USB_ENDPOINT_MASK == direction:
    return ep.bEndpointAddress
  raise Exception('No endpoint found')

 def read(self, length):
  return self.dev.read(self.epIn, length).tostring()

 def write(self, data):
  return self.dev.write(self.epOut, data)


class MtpDriver(UsbDriver):
 """Send and receive PTP/MTP packages to a device. Inspired by libptp2"""
 HEADER_LEN = 12
 MAX_PKG_LEN = 512
 TYPE_COMMAND = 1
 TYPE_DATA = 2
 TYPE_RESPONSE = 3

 def _writePtp(self, type, code, transaction, data=''):
  self.write(dump32le(self.HEADER_LEN + len(data)) + dump16le(type) + dump16le(code) + dump32le(transaction) + data[:self.MAX_PKG_LEN-self.HEADER_LEN])
  if len(data) > self.MAX_PKG_LEN-self.HEADER_LEN:
   self.write(data[self.MAX_PKG_LEN-self.HEADER_LEN:])

 def _readPtp(self):
  data = self.read(self.MAX_PKG_LEN)
  length = parse32le(data[:4])
  type = parse16le(data[4:6])
  code = parse16le(data[6:8])
  transaction = parse32le(data[8:12])
  if length > self.MAX_PKG_LEN:
   data += self.read(length - self.MAX_PKG_LEN)
  return type, code, transaction, data[self.HEADER_LEN:]

 def _readData(self):
  type, code, transaction, data = self._readPtp()
  if type != self.TYPE_DATA:
   raise Exception('Wrong response type: 0x%x' % type)
  return data

 def _readResponse(self):
  type, code, transaction, data = self._readPtp()
  if type != self.TYPE_RESPONSE:
   raise Exception('Wrong response type: 0x%x' % type)
  return code

 def _writeInitialCommand(self, code, args):
  try:
   self.transaction += 1
  except AttributeError:
   self.transaction = 0
  self._writePtp(self.TYPE_COMMAND, code, self.transaction, ''.join([dump32le(arg) for arg in args]))

 def sendCommand(self, code, args):
  """Send a PTP/MTP command without data phase"""
  self._writeInitialCommand(code, args)
  return self._readResponse()

 def sendWriteCommand(self, code, args, data):
  """Send a PTP/MTP command with write data phase"""
  self._writeInitialCommand(code, args)
  self._writePtp(self.TYPE_DATA, code, self.transaction, data)
  return self._readResponse()

 def sendReadCommand(self, code, args):
  """Send a PTP/MTP command with read data phase"""
  self._writeInitialCommand(code, args)
  data = self._readData()
  return self._readResponse(), data
