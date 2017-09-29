import select
import signal
import threading

from ...util import *

UsbSequenceTransferHeader = Struct('UsbSequenceTransferHeader', [
 ('sequence', Struct.INT32),
])

class UsbSequenceTransfer(object):
 def __init__(self, dev, cmd):
  self._dev = dev
  self._cmd = cmd
  self._sequence = 0

 def exec(self, data, bufferSize):
  d = self._dev.sendSonyExtCommand(self._cmd, UsbSequenceTransferHeader.pack(
   sequence = self._sequence
  ) + data, UsbSequenceTransferHeader.size + bufferSize)
  if UsbSequenceTransferHeader.unpack(d[:UsbSequenceTransferHeader.size]).sequence != self._sequence:
   raise Exception("Wrong sequence")
  self._sequence += 1
  return d[UsbSequenceTransferHeader.size:]


USB_STATUS_EOF = 1
USB_STATUS_CANCEL = 1

UsbStatusMsg = Struct('UsbStatusMsg', [
 ('status', Struct.INT32),
])

UsbDataMsg = Struct('UsbDataMsg', [
 ('size', Struct.INT32),
 ('data', Struct.STR % 0xfff8),
])

UsbSocketHeader = Struct('UsbSocketHeader', [
 ('status', Struct.INT32),
 ('rxSize', Struct.INT32),
 ('txSize', Struct.INT32),
])

USB_SOCKET_BUFFER_SIZE = 0xfff4


class ClosedConnection(object):
 def __init__(self):
  self._closed = True

def usb_transfer_socket(transfer, conn):
 if not conn:
  conn = ClosedConnection()

 def sigHandler(sig, frame):
  if not conn._closed:
   print("Aborting...")
   conn.close()
 oldHandler = signal.signal(signal.SIGINT, sigHandler)

 rxBuf = b''
 txBuf = b''
 while True:
  ready = select.select([conn], [conn], [], 0) if not conn._closed else ([], [], [])

  # Write to socket
  if not conn._closed and rxBuf != b'' and ready[1]:
   try:
    n = conn.send(rxBuf)
    rxBuf = rxBuf[n:]
   except (ConnectionAbortedError, ConnectionResetError):
    conn.close()
  if conn._closed:
   rxBuf = b''

  # Read from socket
  if not conn._closed and txBuf == b'' and ready[0]:
   try:
    txBuf = conn.recv(USB_SOCKET_BUFFER_SIZE)
    if txBuf == b'':
     raise ConnectionAbortedError()
   except (ConnectionAbortedError, ConnectionResetError):
    conn.close()

  # Send & receive headers
  masterHeader = UsbSocketHeader.tuple(
   status = USB_STATUS_EOF if conn._closed else 0,
   rxSize = USB_SOCKET_BUFFER_SIZE if rxBuf == b'' else 0,
   txSize = len(txBuf),
  )
  slaveHeader = UsbSocketHeader.unpack(transfer.exec(UsbSocketHeader.pack(**masterHeader._asdict()), UsbSocketHeader.size))

  # Calculate transfer size
  rxSize = min(masterHeader.rxSize, slaveHeader.txSize)
  txSize = min(masterHeader.txSize, slaveHeader.rxSize)

  # End condition
  if masterHeader.status == USB_STATUS_EOF and slaveHeader.status == USB_STATUS_EOF:
   break

  # Close socket if requested
  if not conn._closed and rxBuf == b'' and slaveHeader.status == USB_STATUS_EOF:
   conn.close()

  # Send & receive data
  data = transfer.exec(txBuf[:txSize], rxSize)
  txBuf = txBuf[txSize:]
  if rxSize > 0:
   rxBuf = data

 signal.signal(signal.SIGINT, oldHandler)


def usb_transfer_read(transfer, f):
 abortFlag = threading.Event()

 def sigHandler(sig, frame):
  if not abortFlag.isSet():
   print("Aborting...")
   abortFlag.set()
 oldHandler = signal.signal(signal.SIGINT, sigHandler)

 while True:
  status = UsbStatusMsg.tuple(status = USB_STATUS_CANCEL if abortFlag.isSet() else 0)
  msg = UsbDataMsg.unpack(transfer.exec(UsbStatusMsg.pack(**status._asdict()), UsbDataMsg.size))
  f.write(msg.data[:msg.size])
  if msg.size == 0 or status.status == USB_STATUS_CANCEL:
   break

 signal.signal(signal.SIGINT, oldHandler)


def usb_transfer_write(transfer, f):
 flag = threading.Event()

 def sigHandler(sig, frame):
  if not flag.isSet():
   print("Aborting...")
   flag.set()
 oldHandler = signal.signal(signal.SIGINT, sigHandler)

 while True:
  data = f.read(0xfff8) if not flag.isSet() else b''
  status = UsbStatusMsg.unpack(transfer.exec(UsbDataMsg.pack(
   size = len(data),
   data = data.ljust(0xfff8, b'\0'),
  ), UsbStatusMsg.size))
  if len(data) == 0 or status.status == USB_STATUS_CANCEL:
   break

 signal.signal(signal.SIGINT, oldHandler)
