"""Methods for reading and writing spk files"""

from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

import constants
import util
from ..util import *

SpkHeader = Struct('SpkHeader', [
 ('magic', Struct.STR % 4),
 ('keyOffset', Struct.INT32),
 ('keySize', Struct.INT32),
])
spkHeaderMagic = '1spk'

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
 keyOffset = SpkHeader.size + header.keyOffset
 dataOffset = keyOffset + header.keySize
 return data[keyOffset:dataOffset], data[dataOffset:]

def dumpContainer(encryptedKey, encryptedData):
 """Builds an spk file from the encrypted key and data specified"""
 return SpkHeader.pack(magic=spkHeaderMagic, keyOffset=0, keySize=len(encryptedKey)) + encryptedKey + encryptedData

def decryptKey(encryptedKey):
 """Decrypts an RSA-encrypted key"""
 rsa = RSA.construct((long(constants.rsaModulus), long(constants.rsaExponent)))
 return rsa.encrypt(encryptedKey, 0)[0]

def decryptData(key, encryptedData):
 """Decrypts the apk data using the specified AES key"""
 aes = AES.new(key, AES.MODE_ECB)
 return ''.join(util.unpad(aes.decrypt(c)) for c in util.chunk(encryptedData, constants.blockSize + constants.paddingSize))

def encryptData(key, data):
 """Encrypts the apk data using the specified AES key"""
 aes = AES.new(key, AES.MODE_ECB)
 return ''.join(aes.encrypt(util.pad(c, constants.paddingSize)) for c in util.chunk(data, constants.blockSize))
