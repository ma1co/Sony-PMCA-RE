"""Some methods to manage binary data"""
from ..util import *

def pad(data, size):
 """Applies PKCS#7 padding to the supplied string"""
 n = size - len(data) % size
 return data + n * dump8(n)

def unpad(data):
 """Removes PKCS#7 padding from the supplied string"""
 return data[:-parse8(data[-1:])]

def chunk(data, size):
 """Splits a string in chunks of the given size"""
 return (data[i:i+size] for i in range(0, len(data), size))
