from asn1crypto.cms import ContentInfo
from zipfile import ZipFile

from .axml import parseElements

class ApkParser:
 def __init__(self, file):
  self._file = ZipFile(file)
  self._elements = None

 def _getElements(self):
  if self._elements is None:
   self._elements = list(parseElements(self._file.read('AndroidManifest.xml')))
  return self._elements

 def _getRoot(self):
  return self._getElements()[0]

 def _getElement(self, name):
  return next(e for e in self._getElements() if e.name == name)

 def getPackageName(self):
  return self._getRoot().get('package')

 def getVersionCode(self):
  return int(self._getRoot().get('versionCode'))

 def getVersionName(self):
  return str(self._getRoot().get('versionName'))

 def getMinSdkVersion(self):
  return int(self._getElement('uses-sdk').get('minSdkVersion'))

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
