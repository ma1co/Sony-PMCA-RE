import os
import posixpath
import select
import sys

from ...shell import *
from ...shell.interactive import *

if sys.version_info < (3,):
 # Python 2
 ConnectionError = OSError


def transferSenserTerminal(dev, conn):
 if not conn:
  return

 try:
  while True:
   ready = select.select([conn], [conn], [], 0)

   if ready[1]:
    d = dev.readTerminal()
    conn.sendall(d)

   if ready[0]:
    d = conn.recv(0x40)
    if d == b'':
     break
    dev.writeTerminal(d)

 except (ConnectionError, KeyboardInterrupt):
  pass
 conn.close()


class SenserShell(Shell):
 def __init__(self, dev):
  super(SenserShell, self).__init__("USB service shell")
  self.dev = dev

  self.addCommand('shell', Command(self.shell, (), 'Start an interactive shell'))
  self.addCommand('push', Command(self.push, (2,), 'Copy the specified file from the computer to the device', '<LOCAL> <REMOTE>'))
  self.addCommand('pull', Command(self.pull, (1, 1, ['.']), 'Copy the specified file from the device to the computer', '<REMOTE> [<LOCAL>]'))

 def run(self):
  self.dev.readHasp()
  super(SenserShell, self).run()

 def _openOutputFile(self, fn):
  if os.path.exists(fn):
   i = 1
   while os.path.exists(fn + ('-%d' % i)):
    i += 1
   fn += ('-%d' % i)
  return open(fn, 'wb')

 def shell(self):
  self.dev.setTerminalEnable(False)
  self.dev.setTerminalEnable(True)
  print('Terminal activated. Press <CTRL+C> to exit.')
  run_interactive_shell(lambda conn: transferSenserTerminal(self.dev.dev, conn))
  self.dev.setTerminalEnable(False)

 def push(self, localPath, path):
  with open(localPath, 'rb') as f:
   print('Writing to %s...' % path)
   self.dev.writeFile(path, f.read())

 def pull(self, path, localPath='.'):
  if os.path.isdir(localPath):
   localPath = os.path.join(localPath, posixpath.basename(path))
  with self._openOutputFile(localPath) as f:
   print('Writing to %s...' % f.name)
   self.dev.readFile(path, f)
