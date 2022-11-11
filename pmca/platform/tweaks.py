import abc

from .backend import *
from .backup import *
from ..util import *

class BaseTweak(abc.ABC):
 def available(self):
  try:
   self.enabled()
   return True
  except:
   return False

 @abc.abstractmethod
 def enabled(self):
  pass

 @abc.abstractmethod
 def setEnabled(self, enabled):
  pass

 def strValue(self):
  return 'Enabled' if self.enabled() else 'Disabled'


class BackupTweak(BaseTweak):
 def __init__(self, backup, name, checkValue):
  self._backup = backup
  self._name = name
  self._checkValue = checkValue

 def read(self):
  return self._backup.readProp(self._name)

 def available(self):
  try:
   data = self.read()
   if self._checkValue:
    return data in [self.onValue(), self.offValue()]
   else:
    return True
  except:
   return False

 def enabled(self):
  return self.read() == self.onValue()

 def setEnabled(self, enabled):
  self._backup.writeProp(self._name, self.onValue() if enabled else self.offValue())

 @abc.abstractmethod
 def offValue(self):
  pass

 @abc.abstractmethod
 def onValue(self):
  pass


class BooleanBackupTweak(BackupTweak):
 def __init__(self, backend, name):
  super(BooleanBackupTweak, self).__init__(backend, name, True)

 def offValue(self):
  return b'\x00'

 def onValue(self):
  return b'\x01'


class RecLimitTweak(BackupTweak):
 def __init__(self, backend):
  super(RecLimitTweak, self).__init__(backend, 'recLimit', False)

 def offValue(self):
  return bytearray([0, 29, 50]) # 29m50s

 def onValue(self):
  return bytearray([13, 1, 0]) # 13h01m00s

 def strValue(self):
  hours, minutes, seconds = bytearray(self.read())
  return '%dh %02dm %02ds' % (hours, minutes, seconds)


class RecLimit4kTweak(BackupTweak):
 def __init__(self, backend):
  super(RecLimit4kTweak, self).__init__(backend, 'recLimit4k', False)

 def offValue(self):
  return dump16le(5 * 60) # 5m00s

 def onValue(self):
  return dump16le(0x7fff) # 9h06m07s

 def strValue(self):
  limit = parse16le(self.read())
  hours = limit // 3600
  minutes = (limit - (hours * 3600)) // 60
  seconds = limit % 60
  return '%dh %02dm %02ds' % (hours, minutes, seconds)


class LanguageTweak(BackupTweak):
 BACKUP_LANG_ENABLED = 1
 BACKUP_LANG_DISABLED = 2

 def __init__(self, backend):
  super(LanguageTweak, self).__init__(backend, 'language', False)

 def available(self):
  try:
   val = self.read()
   for v in bytearray(self.read()):
    if v not in [self.BACKUP_LANG_ENABLED, self.BACKUP_LANG_DISABLED]:
     return False
   self.offValue()
   return True
  except:
   return False

 def _getLangs(self, region):
  return bytearray([self.BACKUP_LANG_ENABLED if l else self.BACKUP_LANG_DISABLED for l in self._backup.getDefaultLanguages(region)])

 def offValue(self):
  region = self._backup.getRegion()
  return self._getLangs(region[region.index('_')+1:])

 def onValue(self):
  region = self._backup.getRegion()
  if region[region.index('_')+1:] == 'J1':
    return self._getLangs('JP-MOD')
  else:
    return self._getLangs('ALLLANG')

 def strValue(self):
  val = bytearray(self.read())
  return '%d / %d languages activated' % (sum(1 if l == self.BACKUP_LANG_ENABLED else 0 for l in val), len(val))


class TweakInterface:
 def __init__(self, backend):
  self.backend = backend
  self._tweaks = OrderedDict()

  try:
   self.backupPatch = BackupPatchDataInterface(self.backend)
  except:
   self.backupPatch = None
   return

  backup = BackupInterface(self.backupPatch)
  self.addTweak('recLimit', 'Disable video recording limit', RecLimitTweak(backup))
  self.addTweak('recLimit4k', 'Disable 4K video recording limit', RecLimit4kTweak(backup))
  self.addTweak('language', 'Unlock all languages', LanguageTweak(backup))
  self.addTweak('palNtscSelector', 'Enable PAL / NTSC selector & warning', BooleanBackupTweak(backup, 'palNtscSelector'))
  self.addTweak('usbAppInstaller', 'Enable USB app installer', BooleanBackupTweak(backup, 'usbAppInstaller'))

 def addTweak(self, name, desc, tweak):
  self._tweaks[name] = (desc, tweak)

 def available(self, name):
  return self._tweaks[name][1].available()

 def enabled(self, name):
  return self._tweaks[name][1].enabled()

 def setEnabled(self, name, enabled):
  self._tweaks[name][1].setEnabled(enabled)

 def strValue(self, name):
  return self._tweaks[name][1].strValue()

 def getTweaks(self):
  for name, (desc, tweak) in self._tweaks.items():
   if tweak.available():
    yield name, desc, tweak.enabled(), tweak.strValue()

 def apply(self):
  if self.backupPatch:
   patch = BackupPatchDataInterface(self.backend)
   patch.setPatch(self.backupPatch.getPatch())
   patch.setProtection(True)
   patch.apply()
