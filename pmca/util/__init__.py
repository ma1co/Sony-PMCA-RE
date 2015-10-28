"""Some utility functions to pack and unpack integers"""

import struct

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
 return ord(data)

def dump8(value):
 return chr(value)
