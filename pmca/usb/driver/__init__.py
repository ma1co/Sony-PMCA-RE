from collections import namedtuple

USB_CLASS_PTP = 6
USB_CLASS_MSC = 8

UsbDevice = namedtuple('UsbDevice', 'handle, idVendor, idProduct, type')
