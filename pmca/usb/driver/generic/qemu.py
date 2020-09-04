import socket
import time

from . import *

ADDR = ('localhost', 7642)

USB_RET_STALL = 0xfffffffd

TcpUsbHeader = Struct('TcpUsbHeader', [
 ('flags', Struct.INT8),
 ('ep', Struct.INT8),
 ('', 2),
 ('length', Struct.INT32),
])

UsbSetupPacket = Struct('UsbSetupPacket', [
 ('requestType', Struct.INT8),
 ('request', Struct.INT8),
 ('value', Struct.INT16),
 ('index', Struct.INT16),
 ('length', Struct.INT16),
])

UsbDeviceDescriptor = Struct('UsbDeviceDescriptor', [
 ('', 8),
 ('idVendor', Struct.INT16),
 ('idProduct', Struct.INT16),
 ('', 6),
])

UsbConfigurationDescriptor = Struct('UsbConfigurationDescriptor', [
 ('', 2),
 ('wTotalLength', Struct.INT16),
 ('bNumInterfaces', Struct.INT8),
 ('bConfigurationValue', Struct.INT8),
 ('', 3),
])

UsbInterfaceDescriptor = Struct('UsbInterfaceDescriptor', [
 ('', 2),
 ('bInterfaceNumber', Struct.INT8),
 ('', 1),
 ('bNumEndpoints', Struct.INT8),
 ('binterfaceClass', Struct.INT8),
 ('bInterfaceSubClass', Struct.INT8),
 ('bInterfaceProtocol', Struct.INT8),
 ('', 1),
])

UsbEndpointDescriptor = Struct('UsbEndpointDescriptor', [
 ('', 2),
 ('bEndpointAddress', Struct.INT8),
 ('bmAttributes', Struct.INT8),
 ('', 3),
])

sock = None

class _UsbContext(object):
 def __init__(self, name, classType, driverClass):
  self.name = 'qemu-%s' % name
  self.classType = classType
  self._driverClass = driverClass

 def __enter__(self):
  global sock
  if not sock:
   sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
    sock.settimeout(.5)
    sock.connect(ADDR)
    sock.settimeout(None)
   except socket.timeout:
    sock.close()
    sock = None
  return self

 def __exit__(self, *ex):
  pass

 def listDevices(self, vendor):
  global sock
  if sock:
   dev = _getDevice(UsbBackend(sock), self.classType)
   if dev and dev.idVendor == vendor:
    yield dev

 def openDevice(self, device):
  return self._driverClass(device.handle)


class MscContext(_UsbContext):
 def __init__(self):
  super(MscContext, self).__init__('MSC', USB_CLASS_MSC, MscDriver)

class MtpContext(_UsbContext):
 def __init__(self):
  super(MtpContext, self).__init__('MTP', USB_CLASS_PTP, MtpDriver)


def _getDevice(dev, classType):
 dev.reset()
 config, interfaces = dev.getConfigurationDescriptor(0)
 interface, eps = interfaces[0]
 if interface.binterfaceClass == classType:
  desc = dev.getDeviceDescriptor()
  return UsbDevice(dev, desc.idVendor, desc.idProduct)


class UsbBackend(object):
 FLAG_SETUP = 1
 FLAG_RESET = 2

 DIR_IN = 0x80

 def __init__(self, socket):
  self.socket = socket

 def _req(self, ep, outData=b'', inLength=0, flags=0):
  inData = b''
  l = inLength if ep & self.DIR_IN else len(outData)

  while True:
   request = TcpUsbHeader.pack(flags=flags, ep=ep, length=l)

   for i in range(100):
    time.sleep(.01)
    self.socket.sendall(request)
    if not (ep & self.DIR_IN):
     self.socket.sendall(outData[-l:])
    response = TcpUsbHeader.unpack(self.socket.recv(TcpUsbHeader.size))
    if response.length == USB_RET_STALL:
     raise GenericUsbException()
    elif response.length & 0x80000000 == 0:
     break
   else:
    raise Exception("USB timeout")

   if ep & self.DIR_IN:
    inData += self.socket.recv(response.length)

   l -= response.length
   if l == 0:
    break

  return inData

 def _setup(self, type, request, value=0, index=0, outData=b'', inLength=0):
  l = inLength if type & self.DIR_IN else len(outData)
  header = UsbSetupPacket.pack(requestType=type, request=request, value=value, index=index, length=l)
  self._req(0, header, flags=self.FLAG_SETUP)
  return self._req(type & self.DIR_IN, outData, inLength)

 def _getDescriptor(self, type, index, length, lang=0):
  return self._setup(self.DIR_IN, 6, (type << 8) | index, lang, inLength=length)

 def _setAddress(self, addr):
  self._setup(0, 5, addr)

 def _setConfiguration(self, i):
  self._setup(0, 9, i)

 def reset(self):
  for i in range(2):
   time.sleep(1)
   self._req(0, flags=self.FLAG_RESET)
   time.sleep(1)
   self._req(0, flags=self.FLAG_RESET)
   self.getDeviceDescriptor()
   self._setAddress(1)
   self._setConfiguration(1)

 def clear_halt(self, ep):
  self._setup(2, 1, 0, ep)

 def getDeviceDescriptor(self):
  return UsbDeviceDescriptor.unpack(self._getDescriptor(1, 0, UsbDeviceDescriptor.size))

 def getConfigurationDescriptor(self, i):
  l = UsbConfigurationDescriptor.unpack(self._getDescriptor(2, i, UsbConfigurationDescriptor.size)).wTotalLength
  data = self._getDescriptor(2, i, l)

  config = UsbConfigurationDescriptor.unpack(data)
  offset = UsbConfigurationDescriptor.size

  interfaces = []
  for j in range(config.bNumInterfaces):
   interface = UsbInterfaceDescriptor.unpack(data, offset)
   offset += UsbInterfaceDescriptor.size

   endpoints = []
   for k in range(interface.bNumEndpoints):
    endpoints.append(UsbEndpointDescriptor.unpack(data, offset))
    offset += UsbEndpointDescriptor.size

   interfaces.append((interface, endpoints))

  return config, interfaces

 def getEndpoints(self):
  config, interfaces = self.getConfigurationDescriptor(0)
  interface, eps = interfaces[0]
  return eps

 def read(self, ep, length):
  return self._req(ep, inLength=length)

 def write(self, ep, data):
  return self._req(ep, data)
