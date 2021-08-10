# Source: https://github.com/ajalt/python-sha1
import struct

def _left_rotate(n, b):
 return ((n << b) | (n >> (32 - b))) & 0xffffffff

def sha1(message, length=-1):
 if length < 0:
  length = len(message)
 h0 = 0x67452301
 h1 = 0xEFCDAB89
 h2 = 0x98BADCFE
 h3 = 0x10325476
 h4 = 0xC3D2E1F0
 message += b'\x80'
 message += b'\x00' * ((56 - len(message) % 64) % 64)
 message += struct.pack(b'>Q', length * 8)
 for i in range(0, len(message), 64):
  w = [0] * 80
  for j in range(16):
   w[j] = struct.unpack(b'>I', message[i + j*4:i + j*4 + 4])[0]
  for j in range(16, 80):
   w[j] = _left_rotate(w[j-3] ^ w[j-8] ^ w[j-14] ^ w[j-16], 1)
  a, b, c, d, e = h0, h1, h2, h3, h4
  for i in range(80):
   if 0 <= i <= 19:
    f = d ^ (b & (c ^ d))
    k = 0x5A827999
   elif 20 <= i <= 39:
    f = b ^ c ^ d
    k = 0x6ED9EBA1
   elif 40 <= i <= 59:
    f = (b & c) | (b & d) | (c & d)
    k = 0x8F1BBCDC
   elif 60 <= i <= 79:
    f = b ^ c ^ d
    k = 0xCA62C1D6
   a, b, c, d, e = (_left_rotate(a, 5) + f + e + k + w[i]) & 0xffffffff, a, _left_rotate(b, 30), c, d
  h0 = (h0 + a) & 0xffffffff
  h1 = (h1 + b) & 0xffffffff
  h2 = (h2 + c) & 0xffffffff
  h3 = (h3 + d) & 0xffffffff
  h4 = (h4 + e) & 0xffffffff
 return struct.pack(b'>5I', h0, h1, h2, h3, h4)

def sha1_faulty(message):
 # The sha1 implementation in Sony's senser component has a small bug which is replicated here.
 return sha1(message, len(message) & 0x1f)
