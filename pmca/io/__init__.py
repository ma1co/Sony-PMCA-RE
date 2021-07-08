import os

class ProgressFile:
 def __init__(self, file, total=0):
  if total == 0:
   pos = file.tell()
   file.seek(0, os.SEEK_END)
   total = file.tell() - pos
   file.seek(pos)

  self._file = file
  self._total = total
  self._progress = 0

 def setTotal(self, total=0):
  self._total = total

 def _getPercent(self):
  if self._total == 0:
   return 0
  return int(self._progress * 20 / self._total) * 5

 def _updateProgress(self, size):
  before = self._getPercent()
  self._progress += size
  after = self._getPercent()
  if after != before:
   print('%d%%' % after)

 def read(self, n=-1):
  d = self._file.read(n)
  self._updateProgress(len(d))
  return d

 def write(self, d):
  self._updateProgress(len(d))
  self._file.write(d)
