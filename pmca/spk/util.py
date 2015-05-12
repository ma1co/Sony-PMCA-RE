import struct

def parseInt(data):
 return struct.unpack("<i", data)[0]

def dumpInt(i):
 return struct.pack("<i", i)

def pad(data, size):
 n = size - len(data) % size
 return data + n * chr(n)

def unpad(data):
 return data[:-ord(data[-1])]

def chunk(data, size):
 return (data[i:i+size] for i in xrange(0, len(data), size))
