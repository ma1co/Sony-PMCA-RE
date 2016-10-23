from collections import namedtuple

USB_CLASS_PTP = 6
USB_CLASS_MSC = 8

UsbDevice = namedtuple('UsbDevice', 'handle, idVendor, idProduct, type')

MSC_SENSE_OK = (0, 0, 0)

def parseMscSense(buffer):
 return buffer[2] & 0xf, buffer[12], buffer[13]
