"""Some methods to manage binary data"""

def pad(data, size):
 """Applies PKCS#7 padding to the supplied string"""
 n = size - len(data) % size
 return data + n * chr(n)

def unpad(data):
 """Removes PKCS#7 padding from the supplied string"""
 return data[:-ord(data[-1])]

def chunk(data, size):
 """Splits a string in chunks of the given size"""
 return (data[i:i+size] for i in xrange(0, len(data), size))
