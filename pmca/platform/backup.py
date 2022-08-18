import abc
from collections import OrderedDict
import io

from ..backup import *
from ..util import *

class BaseBackupProp(abc.ABC):
 def __init__(self, dataInterface, size):
  self.dataInterface = dataInterface
  self.size = size

 @abc.abstractmethod
 def read(self):
  pass

 @abc.abstractmethod
 def write(self, data):
  pass


class BackupProp(BaseBackupProp):
 def __init__(self, dataInterface, id, size):
  super(BackupProp, self).__init__(dataInterface, size)
  self.id = id

 def read(self):
  data = self.dataInterface.readProp(self.id)
  if len(data) != self.size:
   raise Exception('Wrong size')
  return data

 def write(self, data):
  if len(data) != self.size:
   raise Exception('Wrong size')
  self.dataInterface.writeProp(self.id, data)


class CompoundBackupProp(BaseBackupProp):
 def __init__(self, dataInterface, props):
  super(CompoundBackupProp, self).__init__(dataInterface, sum(size for id, size in props))
  self._props = [BackupProp(dataInterface, id, size) for id, size in props]

 def read(self):
  return b''.join(prop.read() for prop in self._props)

 def write(self, data):
  if len(data) != self.size:
   raise Exception('Wrong size')
  for prop in self._props:
   prop.write(data[:prop.size])
   data = data[prop.size:]


class BackupDataInterface(abc.ABC):
 @abc.abstractmethod
 def getRegion(self):
  pass

 @abc.abstractmethod
 def readProp(self, id):
  pass

 @abc.abstractmethod
 def writeProp(self, id, data):
  pass


class BackupPlatformDataInterface(BackupDataInterface):
 def __init__(self, backend):
  self.backend = backend

 def getRegion(self):
  return self.backend.getBackupStatus()[0x14:].decode('latin1').rstrip('\0')

 def readProp(self, id):
  return self.backend.readBackup(id)

 def writeProp(self, id, data):
  self.backend.writeBackup(id, data)


class BackupFileDataInterface(BackupDataInterface):
 def __init__(self, file):
  self.backup = BackupFile(file)

 def getRegion(self):
  return self.backup.getRegion()

 def readProp(self, id):
  return self.backup.getProperty(id).data

 def writeProp(self, id, data):
  self.backup.setProperty(id, data)

 def setProtection(self, enabled):
  self.backup.setId1(enabled)

 def getSize(self):
  return self.backup.size

 def updateChecksum(self):
  self.backup.updateChecksum()


class BackupPlatformFileDataInterface(BackupFileDataInterface):
 def __init__(self, backend):
  self.backend = backend
  self.file = io.BytesIO(self.backend.getBackupData())
  super(BackupPlatformFileDataInterface, self).__init__(self.file)

 def apply(self):
  self.updateChecksum()
  data = self.file.getvalue()
  self.backend.setBackupData(data)
  if self.backend.getBackupData()[0x100:self.getSize()] != data[0x100:self.getSize()]:
   raise Exception('Cannot overwrite backup')


class BackupPatchDataInterface(BackupPlatformFileDataInterface):
 def __init__(self, backend):
  super(BackupPatchDataInterface, self).__init__(backend)
  self.patch = {}

 def readProp(self, id):
  if id in self.patch:
   return self.patch[id]
  return super(BackupPatchDataInterface, self).readProp(id)

 def writeProp(self, id, data):
  if len(data) != len(self.backup.getProperty(id).data):
   raise Exception('Wrong data size')
  self.patch[id] = data

 def getPatch(self):
  return self.patch

 def setPatch(self, patch):
  self.patch = patch

 def apply(self):
  if not self.patch:
   return

  patchAttr = {}
  for id, data in self.patch.items():
   p = self.backup.getProperty(id)
   if p.data != data and p.attr & 1:
    patchAttr[id] = p.attr
    self.backup.setPropertyAttr(id, p.attr & ~1)
   self.backup.setProperty(id, data)

  try:
   super(BackupPatchDataInterface, self).apply()
  finally:
   if patchAttr:
    for id, attr in patchAttr.items():
     self.backup.setPropertyAttr(id, attr)
    super(BackupPatchDataInterface, self).apply()


class BackupInterface:
 def __init__(self, dataInterface):
  self.dataInterface = dataInterface
  self._props = OrderedDict()

  self.addProp('androidPlatformVersion', BackupProp(dataInterface, 0x01660024, 8))
  self.addProp('modelCode', BackupProp(dataInterface, 0x00e70000, 5))
  self.addProp('modelName', BackupProp(dataInterface, 0x003e0005, 16))
  self.addProp('serialNumber', BackupProp(dataInterface, 0x00e70003, 4))
  self.addProp('recLimit', CompoundBackupProp(dataInterface, [(0x003c0373 + i, 1) for i in range(3)]))
  self.addProp('recLimit4k', BackupProp(dataInterface, 0x003c04b6, 2))
  self.addProp('palNtscSelector', BackupProp(dataInterface, 0x01070148, 1))
  self.addProp('language', CompoundBackupProp(dataInterface, [(0x010d008f + i, 1) for i in range(35)]))
  self.addProp('usbAppInstaller', BackupProp(dataInterface, 0x01640001, 1))

 def addProp(self, name, prop):
  self._props[name] = prop

 def readProp(self, name):
  return self._props[name].read()

 def writeProp(self, name, data):
  return self._props[name].write(data)

 def getRegion(self):
  return self.dataInterface.getRegion()

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
