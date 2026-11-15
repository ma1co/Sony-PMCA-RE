from axmlparserpy.axmlprinter import AXMLPrinter
from asn1crypto.cms import ContentInfo
import struct
from xml.dom import minidom
from zipfile import ZipFile

class ApkParser:
 def __init__(self, file):
  self._file = ZipFile(file)

 def getManifest(self):
  return minidom.parseString(AXMLPrinter(self._file.read('AndroidManifest.xml')).getBuff())

 def getPackageName(self):
  return self.getManifest().documentElement.getAttribute('package')

 def getVersionCode(self):
  return int(self.getManifest().documentElement.getAttribute('android:versionCode'))

 def getVersionName(self):
  return self.getManifest().documentElement.getAttribute('android:versionName')

 def getMinSdkVersion(self):
  return int(self.getManifest().documentElement.getElementsByTagName('uses-sdk')[0].getAttribute('android:minSdkVersion'))

 def _getCerts(self):
  for info in self._file.infolist():
   if info.filename.startswith('META-INF/') and info.filename.endswith('.RSA'):
    for cert in ContentInfo.load(self._file.read(info))['content']['certificates']:
     yield cert.dump()

 def getCert(self):
  certs = list(self._getCerts())
  if len(certs) != 1:
   raise Exception('Cannot read certificate')
  return certs[0]

 def _getResourceFiles(self, resId):
  """Returns the file paths a resource id points to (all configurations), using resources.arsc"""
  data = self._file.read('resources.arsc')
  def u16(o): return struct.unpack_from('<H', data, o)[0]
  def u32(o): return struct.unpack_from('<I', data, o)[0]

  def readStringPool(o):
   count, flags, stringsStart = u32(o + 8), u32(o + 16), u32(o + 20)
   utf8 = flags & (1 << 8)
   strings = []
   for i in range(count):
    p = o + stringsStart + u32(o + 28 + 4 * i)
    if utf8:
     p += 2 if data[p] & 0x80 else 1
     n = data[p] & 0x7f
     if data[p] & 0x80:
      n = (n << 8) | data[p + 1]
      p += 1
     p += 1
     strings.append(data[p:p + n].decode('utf-8', 'replace'))
    else:
     n = u16(p)
     if n & 0x8000:
      n = ((n & 0x7fff) << 16) | u16(p + 2)
      p += 2
     strings.append(data[p + 2:p + 2 + 2 * n].decode('utf-16-le', 'replace'))
   return strings

  pkgId, typeId, entryId = resId >> 24, (resId >> 16) & 0xff, resId & 0xffff
  globalStrings = None
  files = []
  o = u16(2)
  while o < len(data):
   chunkType, headerSize, size = u16(o), u16(o + 2), u32(o + 4)
   if chunkType == 0x0001 and globalStrings is None:
    globalStrings = readStringPool(o)
   elif chunkType == 0x0200 and u32(o + 8) == pkgId:
    p = o + headerSize
    while p < o + size:
     t, h, sz = u16(p), u16(p + 2), u32(p + 4)
     if t == 0x0201 and data[p + 8] == typeId:
      entryCount, entriesStart = u32(p + 12), u32(p + 16)
      if entryId < entryCount:
       off = u32(p + h + 4 * entryId)
       if off != 0xffffffff:
        e = p + entriesStart + off
        if not u16(e + 2) & 0x0001:  # not a complex entry
         v = e + u16(e)
         if data[v + 3] == 0x03:  # TYPE_STRING
          files.append(globalStrings[u32(v + 4)])
     p += sz
   o += size
  return files

 def getLauncherIconFiles(self):
  """Returns the files used as launcher icon. Framework icons (@android:...) are ignored."""
  manifest = self.getManifest()
  refs = [manifest.getElementsByTagName('application')[0].getAttribute('android:icon')]
  refs += [a.getAttribute('android:icon') for a in manifest.getElementsByTagName('activity')]
  files = []
  for ref in refs:
   if ref.startswith('@'):
    resId = int(ref[1:], 16)
    if resId >> 24 == 0x7f:
     files += self._getResourceFiles(resId)
  return sorted(set(files))

 def getNonBitmapLauncherIcons(self):
  """Sony's launcher (ScalarALauncher) casts app icons to BitmapDrawable. XML/vector icons crash it on every boot."""
  return [f for f in self.getLauncherIconFiles() if not f.lower().endswith('.png')]
