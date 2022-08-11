"""A parser for Backup.bin, the settings file used on Sony cameras"""

from collections import namedtuple

from ..util import *

BackupHeader = Struct('BackupHeader', [
 ('magic', Struct.INT32),
 ('cookie', Struct.INT32),
 ('writeComp', Struct.INT32),
 ('revision', Struct.STR % 4),
 ('numSubsystems', Struct.INT32),
 ('numProperties', Struct.INT32),
 ('dataOffset', Struct.INT32),
 ('dataSize', Struct.INT32),
 ('checksum', Struct.INT32),
 ('...', 4),
 ('id1', Struct.INT32),
 ('...', 0x14),
 ('version', Struct.STR % 0x20),
 ('...', 0x60),
 ('region', Struct.STR % 0x20),
 ('...', 0x20),
])

SubsystemTableEntry = Struct('SubsystemTableEntry', [
 ('numProperties', Struct.INT16),
 ('ptr', Struct.INT32),
])

PropertyTableEntryV2 = Struct('PropertyTableEntryV2', [
 ('attr', Struct.INT8),
 ('ptr', Struct.INT32),
])

PropertyTableEntryV4 = Struct('PropertyTableEntryV4', [
 ('attr', Struct.INT16),
 ('ptr', Struct.INT32),
])

OversizeProperty = Struct('OversizeProperty', [
 ('size', Struct.INT16),
])

VariableSizeProperty = Struct('VariableSizeProperty', [
 ('size', Struct.INT16),
 ('maxSize', Struct.INT16),
])

BackupPropertyPtr = namedtuple('BackupPropertyPtr', 'attr, size, maxSize, ptr')

BackupProperty = namedtuple('BackupProperty', 'attr, data, resetData')

class BackupFile:
 def __init__(self, file):
  self.file = file

  self.header = BackupHeader.unpack(self.file)
  if self.header.revision[:2] != b'BK' or self.header.revision[3:] != b'\0':
   raise Exception('Invalid backup file')

  self.revision = int(self.header.revision[2:3])
  if self.revision not in [2, 4]:
   raise Exception('Invalid backup revision')

  self.size = self.header.dataOffset + self.header.dataSize
  if self.header.checksum != self._calcChecksum():
   raise Exception('Wrong checksum')

  self.PropertyTableEntry = PropertyTableEntryV4 if self.revision >= 4 else PropertyTableEntryV2
  self.subsystemTableOffset = BackupHeader.size
  self.propertyTableOffset = self.subsystemTableOffset + self.header.numSubsystems * SubsystemTableEntry.size
  if self.propertyTableOffset + self.header.numProperties * self.PropertyTableEntry.size > self.header.dataOffset:
   raise Exception('Invalid data offset')

 def _read32(self, off):
  self.file.seek(off)
  return parse32le(self.file.read(4))

 def _write32(self, off, value):
  self.file.seek(off)
  return self.file.write(dump32le(value))

 def _calcChecksum(self):
  self.file.seek(0)
  data = self.file.read(self.size)
  return sum(bytearray(data[:0x20] + data[0x24:]))

 def updateChecksum(self):
  self._write32(0x20, self._calcChecksum())

 def getRegion(self):
  return self.header.region.decode('latin1').rstrip('\0')

 def getId1(self):
  return self._read32(0x28)

 def setId1(self, enable):
  return self._write32(0x28, 1 if enable else 0)

 def _readSubsystemTable(self, i):
  if i >= self.header.numSubsystems:
   raise Exception('Invalid subsystem id')
  s = SubsystemTableEntry.unpack(self.file, self.subsystemTableOffset + i * SubsystemTableEntry.size)
  if s.ptr + s.numProperties > self.header.numProperties:
   raise Exception('Invalid subsystem')
  return s

 def _getPropertyTableOffset(self, id):
  subsystem = self._readSubsystemTable(id >> 16)
  i = id & 0xffff
  if i >= subsystem.numProperties:
   raise Exception('Invalid property id')
  return self.propertyTableOffset + (subsystem.ptr + i) * self.PropertyTableEntry.size

 def _readPropertyTable(self, id):
  return self.PropertyTableEntry.unpack(self.file, self._getPropertyTableOffset(id))

 def _writePropertyTable(self, id, attr, ptr):
  self.file.seek(self._getPropertyTableOffset(id))
  self.file.write(self.PropertyTableEntry.pack(attr=attr, ptr=ptr))

 def _readProperty(self, id):
  property = self._readPropertyTable(id)
  if property.ptr == 0xffffffff:
   raise Exception('Invalid property')

  size = property.ptr >> 24
  maxSize = size
  offset = property.ptr & 0xffffff

  if offset < self.header.dataOffset:
   raise Exception('Invalid offset')

  if size == 0xff:
   op = OversizeProperty.unpack(self.file, offset)
   size = op.size
   maxSize = op.size
   offset += OversizeProperty.size
  elif size == 0:
   vp = VariableSizeProperty.unpack(self.file, offset)
   size = vp.size
   maxSize = vp.maxSize
   offset += VariableSizeProperty.size

  if size > maxSize or offset + maxSize > self.size:
   raise Exception('Invalid size')

  return BackupPropertyPtr(property.attr, size, maxSize, offset)

 def getProperty(self, id):
  p = self._readProperty(id)

  self.file.seek(p.ptr)
  data = self.file.read(p.size)
  resetData = None

  if p.attr & 0x01:# property is read only, cannot be written with Backup_write()
   pass
  if p.attr & 0x02:# property is protected, won't be changed by Backup_protect()
   pass
  if p.attr & 0x08:# callbacks are triggered when this property is written with Backup_write()
   pass
  if p.attr & 0x74:# property can be reset with Backup_reset()
   self.file.seek(p.ptr + p.maxSize)
   resetData = self.file.read(p.size)
  if p.attr & 0x80:# property data is an array that can be read with Backup_read_setting_attr()
   # there are ord(backupProperties[0x3e000c].data)+1 elements in the array
   pass

  return BackupProperty(p.attr, data, resetData)

 def setProperty(self, id, data):
  p = self._readProperty(id)
  if len(data) != p.size:
   raise Exception('Wrong data size')
  self.file.seek(p.ptr)
  self.file.write(data)

 def setPropertyAttr(self, id, attr):
  self._writePropertyTable(id, attr, self._readPropertyTable(id).ptr)

 def listProperties(self):
  for i in range(self.header.numSubsystems):
   for j in range(self._readSubsystemTable(i).numProperties):
    id = i << 16 | j
    p = self._readPropertyTable(id)
    if p.ptr != 0xffffffff:
     yield id, self.getProperty(id)
