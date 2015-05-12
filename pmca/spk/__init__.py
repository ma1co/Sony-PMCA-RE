from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

import constants
import util

def parse(data):
 encryptedKey, encryptedData = parseContainer(data)
 key = decryptKey(encryptedKey)
 return decryptData(key, encryptedData)

def dump(data):
 encryptedKey = constants.sampleSpkKey
 key = decryptKey(encryptedKey)
 encryptedData = encryptData(key, data)
 return dumpContainer(encryptedKey, encryptedData)

def parseContainer(data):
 if data[:4] != constants.header:
  raise
 offset = util.parseInt(data[4:8])
 keyLen = util.parseInt(data[offset+8:offset+12])
 return data[offset+12:offset+12+keyLen], data[offset+12+keyLen:]

def dumpContainer(encryptedKey, encryptedData):
 return constants.header + util.dumpInt(0) + util.dumpInt(len(encryptedKey)) + encryptedKey + encryptedData

def decryptKey(encryptedKey):
 rsa = RSA.construct((long(constants.rsaModulus), long(constants.rsaExponent)))
 return rsa.encrypt(encryptedKey, 0)[0]

def decryptData(key, encryptedData):
 aes = AES.new(key, AES.MODE_ECB)
 return ''.join(util.unpad(aes.decrypt(c)) for c in util.chunk(encryptedData, constants.blockSize + constants.paddingSize))

def encryptData(key, data):
 aes = AES.new(key, AES.MODE_ECB)
 return ''.join(aes.encrypt(util.pad(c, constants.paddingSize)) for c in util.chunk(data, constants.blockSize))
