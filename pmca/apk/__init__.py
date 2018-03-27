from apkutils.axml.axmlparser import AXML
from asn1crypto.cms import ContentInfo
from zipfile import ZipFile

class ApkParser:
 def __init__(self, file):
  self._file = ZipFile(file)

 def getManifest(self):
  return AXML(self._file.read('AndroidManifest.xml')).get_xml_obj()

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
