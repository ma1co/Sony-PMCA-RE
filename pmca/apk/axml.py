"""Minimal parser for Android binary XML (AndroidManifest.xml inside an apk).

Only what pmca needs: the attributes of the root element and of the uses-sdk
element. Supports both UTF-8 and UTF-16 string pools, which the old
axmlparserpy dependency did not.
"""
import struct

RES_STRING_POOL_TYPE = 0x0001
RES_XML_RESOURCE_MAP_TYPE = 0x0180
RES_XML_START_ELEMENT_TYPE = 0x0102

UTF8_FLAG = 1 << 8

TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12

# Attribute names for manifests which have been stripped of their name strings
RESOURCE_NAMES = {
 0x0101021b: 'versionCode',
 0x0101021c: 'versionName',
 0x0101020c: 'minSdkVersion',
}


class AxmlElement:
 def __init__(self, name, attributes):
  self.name = name
  self.attributes = attributes

 def get(self, name, default=None):
  return self.attributes.get(name, default)


def _readStringPool(data, start):
 (stringCount, styleCount, flags, stringsStart) = struct.unpack_from('<IIII', data, start + 8)
 offsets = struct.unpack_from('<%dI' % stringCount, data, start + 28)
 base = start + stringsStart
 strings = []
 for offset in offsets:
  pos = base + offset
  if flags & UTF8_FLAG:
   # Two lengths (character count, byte count), each 1 or 2 bytes
   for _ in range(2):
    length = data[pos]
    pos += 1
    if length & 0x80:
     length = ((length & 0x7f) << 8) | data[pos]
     pos += 1
   strings.append(data[pos:pos+length].decode('utf-8', 'replace'))
  else:
   length = struct.unpack_from('<H', data, pos)[0]
   pos += 2
   if length & 0x8000:
    length = ((length & 0x7fff) << 16) | struct.unpack_from('<H', data, pos)[0]
    pos += 2
   strings.append(data[pos:pos+2*length].decode('utf-16-le', 'replace'))
 return strings


def _readResourceMap(data, start, chunkSize):
 count = (chunkSize - 8) // 4
 return struct.unpack_from('<%dI' % count, data, start + 8)


def parseElements(data):
 """Yields AxmlElement for every start element in document order"""
 strings = []
 resourceIds = []

 (fileType, headerSize, fileSize) = struct.unpack_from('<HHI', data, 0)
 pos = headerSize
 while pos + 8 <= min(len(data), fileSize):
  (chunkType, chunkHeaderSize, chunkSize) = struct.unpack_from('<HHI', data, pos)
  if chunkSize < 8:
   break
  if chunkType == RES_STRING_POOL_TYPE:
   strings = _readStringPool(data, pos)
  elif chunkType == RES_XML_RESOURCE_MAP_TYPE:
   resourceIds = _readResourceMap(data, pos, chunkSize)
  elif chunkType == RES_XML_START_ELEMENT_TYPE:
   yield _readStartElement(data, pos, chunkHeaderSize, strings, resourceIds)
  pos += chunkSize


def _attributeName(index, strings, resourceIds):
 name = strings[index] if index < len(strings) else ''
 if not name and index < len(resourceIds):
  name = RESOURCE_NAMES.get(resourceIds[index], '')
 return name


def _readStartElement(data, start, headerSize, strings, resourceIds):
 body = start + headerSize
 (ns, nameIndex, attributeStart, attributeSize, attributeCount) = struct.unpack_from('<IIHHH', data, body)
 name = strings[nameIndex] if nameIndex < len(strings) else ''
 attributes = {}
 pos = body + attributeStart
 for _ in range(attributeCount):
  (attrNs, attrNameIndex, rawValue, size, res0, dataType, value) = struct.unpack_from('<IIIHBBI', data, pos)
  attrName = _attributeName(attrNameIndex, strings, resourceIds)
  if rawValue != 0xffffffff:
   attrValue = strings[rawValue] if rawValue < len(strings) else ''
  elif dataType == TYPE_STRING:
   attrValue = strings[value] if value < len(strings) else ''
  elif dataType == TYPE_INT_BOOLEAN:
   attrValue = bool(value)
  else:
   attrValue = value
  attributes[attrName] = attrValue
  pos += attributeSize
 return AxmlElement(name, attributes)
