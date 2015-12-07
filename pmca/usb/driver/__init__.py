from collections import namedtuple

USB_CLASS_PTP = 6

UsbDevice = namedtuple('UsbDevice', 'handle, idVendor, idProduct, type')
