"""Firmware data file parser"""

import os
from ..util import *

DatHeader = Struct('DatHeader', [
 ('magic', Struct.STR % 8),
])
datHeaderMagic = b'\x89\x55\x46\x55\x0d\x0a\x1a\x0a'

DatChunkHeader = Struct('DatChunkHeader', [
 ('size', Struct.INT32),
 ('type', Struct.STR % 4),
], Struct.BIG_ENDIAN)

def readDat(file):
 """"Extract the firmware from a .dat file. Returns the offset and the size of the firmware data."""
 file.seek(0)
 header = DatHeader.unpack(file.read(DatHeader.size))
 if header.magic != datHeaderMagic:
  raise Exception('Wrong magic')

 while True:
  data = file.read(DatChunkHeader.size)
  if len(data) != DatChunkHeader.size:
   break
  chunk = DatChunkHeader.unpack(data)
  if chunk.type == b'FDAT':
   return file.tell(), chunk.size
  file.seek(chunk.size, os.SEEK_CUR)
 raise Exception('FDAT chunk not found')
