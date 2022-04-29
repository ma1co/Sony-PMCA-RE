import select

from . import *

class SenserPlatformBackend(ShellPlatformBackend, FilePlatformBackend, MemoryPlatformBackend):
 def __init__(self, dev):
  self.dev = dev

 def start(self):
  self.dev.readHasp()

 def interactiveShell(self, conn):
  self.dev.setTerminalEnable(False)
  self.dev.setTerminalEnable(True)
  print('Terminal activated. Press <CTRL+C> to exit.')
  self.transferSenserTerminal(conn)
  self.dev.setTerminalEnable(False)

 def writeFile(self, path, f):
  self.dev.writeFile(path, f.read())

 def readFile(self, path, f, sizeCb=None):
  self.dev.readFile(path, f)

 def readMemory(self, offset, size, f):
  self.dev.readMemory(offset, size, f)

 def transferSenserTerminal(self, conn):
  if not conn:
   return

  try:
   while True:
    ready = select.select([conn], [conn], [], 0)

    if ready[1]:
     d = self.dev.dev.readTerminal()
     conn.sendall(d)

    if ready[0]:
     d = conn.recv(0x40)
     if d == b'':
      break
     self.dev.dev.writeTerminal(d)

  except (ConnectionError, KeyboardInterrupt):
   pass
  conn.close()
