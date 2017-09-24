"""Methods for reading and writing spk files"""

import sys

try:
 from Cryptodome.Cipher import AES
 from Cryptodome.PublicKey import RSA
 from Cryptodome.Util.number import bytes_to_long, long_to_bytes
except ImportError:
 from Crypto.Cipher import AES
 from Crypto.PublicKey import RSA
 from Crypto.Util.number import bytes_to_long, long_to_bytes

if sys.version_info >= (3,):
 long = int

from . import constants
from . import util
from ..util import *

SpkHeader = Struct('SpkHeader', [
 ('magic', Struct.STR % 4),
 ('keyOffset', Struct.INT32),
])
spkHeaderMagic = b'1spk'

SpkKeyHeader = Struct('SpkKeyHeader', [
 ('keySize', Struct.INT32),
])

def parse(data):
 """Parses an spk file

 Returns:
  The contained apk data
 """
 encryptedKey, encryptedData = parseContainer(data)
 key = decryptKey(encryptedKey)
 return decryptData(key, encryptedData)

def dump(data):
 """Builds an spk file containing the apk data specified"""
 encryptedKey = constants.sampleSpkKey
 key = decryptKey(encryptedKey)
 encryptedData = encryptData(key, data)
 return dumpContainer(encryptedKey, encryptedData)

def isSpk(data):
 return len(data) >= SpkHeader.size and SpkHeader.unpack(data).magic == spkHeaderMagic

def parseContainer(data):
 """Parses an spk file

 Returns:
  ('encrypted key', 'encrypted apk data')
 """
 header = SpkHeader.unpack(data)
 if header.magic != spkHeaderMagic:
  raise Exception('Wrong magic')
 keyHeaderOffset = SpkHeader.size + header.keyOffset
 keyHeader = SpkKeyHeader.unpack(data, keyHeaderOffset)
 keyOffset = keyHeaderOffset + SpkKeyHeader.size
 dataOffset = keyOffset + keyHeader.keySize
 return data[keyOffset:dataOffset], data[dataOffset:]

def dumpContainer(encryptedKey, encryptedData):
 """Builds an spk file from the encrypted key and data specified"""
 return SpkHeader.pack(magic=spkHeaderMagic, keyOffset=0) + SpkKeyHeader.pack(keySize=len(encryptedKey)) + encryptedKey + encryptedData

def decryptKey(encryptedKey):
 """Decrypts an RSA-encrypted key"""
 rsa = RSA.construct((long(constants.rsaModulus), long(constants.rsaExponent)))
 try:
  return rsa.encrypt(encryptedKey, 0)[0]
 except NotImplementedError:
  # pycryptodome
  return long_to_bytes(rsa._encrypt(bytes_to_long(encryptedKey)))

def decryptData(key, encryptedData):
 """Decrypts the apk data using the specified AES key"""
 aes = AES.new(key, AES.MODE_ECB)
 return b''.join(util.unpad(aes.decrypt(c)) for c in util.chunk(encryptedData, constants.blockSize + constants.paddingSize))

def encryptData(key, data):
 """Encrypts the apk data using the specified AES key"""
 aes = AES.new(key, AES.MODE_ECB)
 return b''.join(aes.encrypt(util.pad(c, constants.paddingSize)) for c in util.chunk(data, constants.blockSize))
