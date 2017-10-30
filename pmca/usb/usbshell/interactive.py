import contextlib
import signal
import socket
import sys
import threading

if sys.version_info < (3,):
 # Python 2
 ConnectionError = OSError

from .transfer import *

def usb_transfer_interactive_shell(transfer, stdin=True, stdout=True, port=5005):
 addr = '127.0.0.1'

 readyFlag = threading.Event()
 t = threading.Thread(target=console_loop, args=(addr, port, readyFlag, stdin, stdout))
 t.setDaemon(True)
 t.start()

 usb_start_socket_server(transfer, addr, port, readyFlag)

 try:
  t.join()
 except KeyboardInterrupt:
  pass


def usb_start_socket_server(transfer, addr, port, readyFlag=None):
 with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
  abortFlag = threading.Event()

  def sigHandler(sig, frame):
   if not abortFlag.isSet():
    print("Aborting...")
    abortFlag.set()
  oldHandler = signal.signal(signal.SIGINT, sigHandler)

  sock.settimeout(1)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.bind((addr, port))
  sock.listen(0)

  if readyFlag:
   readyFlag.set()

  while True:
   try:
    conn, addr = sock.accept()
    break
   except socket.timeout:
    if abortFlag.isSet():
     conn = None
     break

  signal.signal(signal.SIGINT, oldHandler)
  usb_transfer_socket(transfer, conn)


def console_loop(addr, port, readyFlag=None, stdin=True, stdout=True):
 if readyFlag:
  readyFlag.wait()
 with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
  sock.connect((addr, port))
  stopped = threading.Event()
  if stdin:
   t = threading.Thread(target=stdin_loop, args=(sock, stopped))
   t.setDaemon(True)
   t.start()
  if stdout:
   stdout_loop(sock)
  stopped.set()
  if stdin:
   print('Please press enter')
   t.join()


def stdin_loop(sock, stoppedFlag):
 while not stoppedFlag.isSet():
  try:
   sock.send(sys.stdin.readline().encode('latin1', 'replace'))
  except ConnectionError:
   break


def stdout_loop(sock):
 while True:
  try:
   d = sock.recv(4096)
   if d == b'':
    raise ConnectionError()
   sys.stdout.write(d.decode('latin1', 'replace'))
   sys.stdout.flush()
  except ConnectionError:
   break
