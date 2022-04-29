import abc
from collections import OrderedDict

from ..util import *

class BaseBackupProp(abc.ABC):
 def __init__(self, backend, size):
  self.backend = backend
  self.size = size

 @abc.abstractmethod
 def read(self):
  pass

 @abc.abstractmethod
 def write(self, data):
  pass


class BackupProp(BaseBackupProp):
 def __init__(self, backend, id, size):
  super(BackupProp, self).__init__(backend, size)
  self.id = id

 def read(self):
  data = self.backend.readBackup(self.id)
  if len(data) != self.size:
   raise Exception('Wrong size')
  return data

 def write(self, data):
  if len(data) != self.size:
   raise Exception('Wrong size')
  self.backend.writeBackup(self.id, data)


class CompoundBackupProp(BaseBackupProp):
 def __init__(self, backend, props):
  super(CompoundBackupProp, self).__init__(backend, sum(size for id, size in props))
  self._props = [BackupProp(backend, id, size) for id, size in props]

 def read(self):
  return b''.join(prop.read() for prop in self._props)

 def write(self, data):
  if len(data) != self.size:
   raise Exception('Wrong size')
  for prop in self._props:
   prop.write(data[:prop.size])
   data = data[prop.size:]


class BackupInterface:
 BACKUP_PRESET_DATA_OFFSET_VERSION = 0x0c
 BACKUP_PRESET_DATA_OFFSET_ID1 = 0x28

 def __init__(self, backend):
  self.backend = backend
  self._props = OrderedDict()

  self.addProp('androidPlatformVersion', BackupProp(backend, 0x01660024, 8))
  self.addProp('modelCode', BackupProp(backend, 0x00e70000, 5))
  self.addProp('modelName', BackupProp(backend, 0x003e0005, 16))
  self.addProp('serialNumber', BackupProp(backend, 0x00e70003, 4))
  self.addProp('recLimit', CompoundBackupProp(backend, [(0x003c0373 + i, 1) for i in range(3)]))
  self.addProp('recLimit4k', BackupProp(backend, 0x003c04b6, 2))
  self.addProp('palNtscSelector', BackupProp(backend, 0x01070148, 1))
  self.addProp('language', CompoundBackupProp(backend, [(0x010d008f + i, 1) for i in range(35)]))
  self.addProp('usbAppInstaller', BackupProp(backend, 0x01640001, 1))

 def addProp(self, name, prop):
  self._props[name] = prop

 def readProp(self, name):
  return self._props[name].read()

 def writeProp(self, name, data):
  return self._props[name].write(data)

 def getRegion(self):
  return self.backend.getBackupStatus()[0x14:].decode('latin1').rstrip('\0')

 def getProtection(self):
  data = self.backend.getBackupData()
  version = data[self.BACKUP_PRESET_DATA_OFFSET_VERSION:self.BACKUP_PRESET_DATA_OFFSET_VERSION+4]
  if version not in [b'BK%d\0' % i for i in [2, 3, 4]]:
   raise Exception('Unsupported backup version')
  return parse32le(data[self.BACKUP_PRESET_DATA_OFFSET_ID1:self.BACKUP_PRESET_DATA_OFFSET_ID1+4]) != 0

 def getDefaultLanguages(self, region):
  return {
   'ALLLANG': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
   'AP2': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
   'AU2': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'CA2': [1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
   'CE':  [1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
   'CE3': [1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
   'CE7': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'CEC': [1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0],
   'CEH': [1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
   'CN1': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'CN2': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
   'E32': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'E33': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'E37': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'E38': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
   'EA8': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'HK1': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'IN5': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
   'J1':  [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
   'JE3': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
   'KR2': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'RU2': [1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
   'RU3': [1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0],
   'TW6': [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
   'U2':  [1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
   'UC2': [1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  }[region]
