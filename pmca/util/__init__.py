"""Some utility functions to pack and unpack integers"""

import struct
from collections import namedtuple

def parse32le(data):
 return struct.unpack('<I', data)[0]

def dump32le(value):
 return struct.pack('<I', value)

def parse32be(data):
 return struct.unpack('>I', data)[0]

def dump32be(value):
 return struct.pack('>I', value)

def parse16le(data):
 return struct.unpack('<H', data)[0]

def dump16le(value):
 return struct.pack('<H', value)

def parse16be(data):
 return struct.unpack('>H', data)[0]

def dump16be(value):
 return struct.pack('>H', value)

def parse8(data):
 return struct.unpack('B', data)[0]

def dump8(value):
 return struct.pack('B', value)

class Struct(object):
 LITTLE_ENDIAN = '<'
 BIG_ENDIAN = '>'
 PADDING = '%dx'
 CHAR = 'c'
 STR = '%ds'
 INT64 = 'Q'
 INT32 = 'I'
 INT16 = 'H'
 INT8 = 'B'

 def __init__(self, name, fields, byteorder=LITTLE_ENDIAN):
  self.tuple = namedtuple(name, (n for n, fmt in fields if not isinstance(fmt, int)))
  self.format = byteorder + ''.join(self.PADDING % fmt if isinstance(fmt, int) else fmt for n, fmt in fields)
  self.size = struct.calcsize(self.format)

 def unpack(self, data, offset = 0):
  return self.tuple(*struct.unpack_from(self.format, data, offset))

 def pack(self, **kwargs):
  return struct.pack(self.format, *self.tuple(**kwargs))
