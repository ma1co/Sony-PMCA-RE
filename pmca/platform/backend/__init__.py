import abc

class PlatformBackend(object):
 def start(self):
  pass

 def stop(self):
  pass


class ShellPlatformBackend(PlatformBackend, abc.ABC):
 @abc.abstractmethod
 def interactiveShell(self, conn):
  pass


class FilePlatformBackend(PlatformBackend, abc.ABC):
 @abc.abstractmethod
 def writeFile(self, path, f):
  pass

 @abc.abstractmethod
 def readFile(self, path, f, sizeCb=None):
  pass


class MemoryPlatformBackend(PlatformBackend, abc.ABC):
 @abc.abstractmethod
 def readMemory(self, offset, size, f):
  pass


class BootloaderPlatformBackend(PlatformBackend, abc.ABC):
 @abc.abstractmethod
 def readBootloader(self):
  pass


class AndroidPlatformBackend(PlatformBackend, abc.ABC):
 @abc.abstractmethod
 def mountAndroidData(self):
  pass

 @abc.abstractmethod
 def unmountAndroidData(self, commitBackup):
  pass


class BackupPlatformBackend(PlatformBackend, abc.ABC):
 @abc.abstractmethod
 def readBackup(self, id):
  pass

 @abc.abstractmethod
 def writeBackup(self, id, data):
  pass

 @abc.abstractmethod
 def syncBackup(self):
  pass

 @abc.abstractmethod
 def getBackupStatus(self):
  pass

 @abc.abstractmethod
 def getBackupData(self):
  pass

 @abc.abstractmethod
 def setBackupProtection(self, enable):
  pass
