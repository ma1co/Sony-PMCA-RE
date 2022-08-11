import os
import posixpath

from .android import *
from .backend import *
from .backup import *
from .properties import *
from .tweaks import *
from ..io import *
from ..shell import *
from ..shell.interactive import *
from ..shell.parser import *


class CameraShell(Shell):
 def __init__(self, backend):
  super(CameraShell, self).__init__("platform shell")
  self.backend = backend

  self.addCommand('info', Command(self.info, (), 'Print device info'))

  if isinstance(self.backend, ShellPlatformBackend):
   self.addCommand('shell', Command(self.shell, (), 'Start an interactive shell'))

  if isinstance(self.backend, FilePlatformBackend):
   self.addCommand('push', Command(self.push, (2,), 'Copy the specified file from the computer to the device', '<LOCAL> <REMOTE>'))
   self.addCommand('pull', Command(self.pull, (1, 1, ['.']), 'Copy the specified file from the device to the computer', '<REMOTE> [<LOCAL>]'))

  if isinstance(self.backend, BootloaderPlatformBackend):
   self.addCommand('bootloader', Command(self.bootloader, (0, 1, ['.']), 'Dump the boot loader', '[<OUTDIR>]'))

  if isinstance(self.backend, MemoryPlatformBackend):
   self.addCommand('bootrom', Command(self.bootrom, (0, 1, ['.']), 'Dump the boot rom', '[<OUTDIR>]'))

  if isinstance(self.backend, AndroidPlatformBackend):
   self.addCommand('install', Command(self.install, (1,), 'Install the specified android app', '<APKFILE>'))

  if isinstance(self.backend, BackupPlatformBackend):
   self.addCommand('tweak', Command(self.tweak, (), 'Tweak device settings'))

   bk = SubCommand()
   bk.addCommand('r', Command(self.readBackup, (1,), 'Read backup property', '<ID>'))
   bk.addCommand('w', ResidueCommand(self.writeBackup, 1, 'Write backup property', '<ID> <DATA>'))
   bk.addCommand('s', Command(self.syncBackup, (), 'Sync backup data to disk'))
   bk.addCommand('lock', Command(self.lockBackup, (), 'Lock protected backup settings'))
   bk.addCommand('unlock', Command(self.unlockBackup, (), 'Unlock protected backup settings'))
   self.addCommand('bk', bk)

 def run(self):
  self.backend.start()
  super(CameraShell, self).run()
  self.backend.stop()

 def _openOutputFile(self, fn):
  if os.path.exists(fn):
   i = 1
   while os.path.exists(fn + ('-%d' % i)):
    i += 1
   fn += ('-%d' % i)
  return open(fn, 'wb')

 def info(self):
  for id, desc, value in PropertyInterface(self.backend).getProps():
   print('%-20s%s' % (desc + ': ', value))

 def shell(self):
  run_interactive_shell(self.backend.interactiveShell)

 def push(self, localPath, path):
  with open(localPath, 'rb') as f:
   print('Writing to %s...' % path)
   self.backend.writeFile(path, ProgressFile(f))

 def pull(self, path, localPath='.'):
  if os.path.isdir(localPath):
   localPath = os.path.join(localPath, posixpath.basename(path))
  with self._openOutputFile(localPath) as f:
   print('Writing to %s...' % f.name)
   p = ProgressFile(f)
   self.backend.readFile(path, p, p.setTotal)

 def bootloader(self, localPath='.'):
  if not os.path.isdir(localPath):
   raise Exception('%s is not a directory' % localPath)
  for i, data in enumerate(self.backend.readBootloader()):
   with self._openOutputFile(os.path.join(localPath, 'boot%d' % (i + 1))) as f:
    print('Writing to %s...' % f.name)
    f.write(data)

 def bootrom(self, localPath='.'):
  if os.path.isdir(localPath):
   localPath = os.path.join(localPath, 'bootrom')
  with self._openOutputFile(localPath) as f:
   print('Writing to %s...' % f.name)
   self.backend.readMemory(0xffff0000, 0x6000, f)

 def install(self, apkFile):
  with open(apkFile, 'rb') as f:
   AndroidInterface(self.backend).installApk(f)

 def readBackup(self, id):
  id = int(id, 16)
  value = self.backend.readBackup(id)
  print(' '.join('%02x' % ord(value[i:i+1]) for i in range(len(value))))

 def writeBackup(self, id, data):
  id = int(id, 16)
  value = []
  parser = ArgParser(data)
  if not parser.available():
   raise ValueError('Not enough arguments provided')
  while parser.available():
   value.append(int(parser.consumeRequiredArg(), 16))
  self.backend.writeBackup(id, bytes(bytearray(value)))
  print('Success')

 def syncBackup(self):
  self.backend.syncBackup()

 def lockBackup(self):
  self.backend.setBackupProtection(True)

 def unlockBackup(self):
  self.backend.setBackupProtection(False)

 def tweak(self):
  tweakInterface = TweakInterface(self.backend)
  while True:
   tweaks = list(tweakInterface.getTweaks())
   if not tweaks:
    print('No tweaks available')
    break

   for i, (id, desc, status, value) in enumerate(tweaks):
    print('%d: [%s] %s' % (i + 1, ('X' if status else ' '), desc))
    print('       %s' % value)
    print('')

   try:
    while True:
     try:
      i = int(input('Enter number of tweak to toggle (0 to apply): '))
      if 0 <= i <= len(tweaks):
       break
     except ValueError:
      pass
   except KeyboardInterrupt:
    print('')
    break

   if i == 0:
    tweakInterface.apply()
    break
   else:
    id, desc, status, value = tweaks[i - 1]
    tweakInterface.setEnabled(id, not status)
    print('')
