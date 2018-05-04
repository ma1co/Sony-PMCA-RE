import binascii
from xml.dom import minidom

from ...apk import *

def installApk(shell, apkFile):
 apk = ApkParser(apkFile)

 # Mount android data partition
 dataDir = shell.mountAndroidData()
 commitBackup = False

 # Patch packages.xml
 xmlFile = dataDir + '/system/packages.xml'
 xmlData = patchXml(shell.readFile(xmlFile), apk.getPackageName(), apk.getCert())
 if xmlData:
  shell.writeFile(xmlFile, xmlData)
  commitBackup = True

 # Write apk
 from . import UsbShellException
 i = 0
 while True:
  path = '%s/app/app-%d.apk' % (dataDir, i)
  try:
   shell.getFileSize(path)
  except UsbShellException:
   break
  i += 1
 apkFile.seek(0)
 shell.writeFile(path, apkFile.read())

 # Unmount android data partition
 shell.unmountAndroidData(commitBackup)

def patchXml(xmlData, packageName, certKey):
 xml = minidom.parseString(xmlData)

 # Parse packages.xml
 packageElementsByName = {}
 certKeysByIndex = {}
 definedCertIndexesByName = {}
 dependantCertElementsByIndex = {}
 for packageElement in xml.getElementsByTagName('package'):
  name = packageElement.getAttribute('name')
  packageElementsByName[name] = packageElement
  for certElement in packageElement.getElementsByTagName('sigs')[0].getElementsByTagName('cert'):
   index = int(certElement.getAttribute('index'))
   if certElement.hasAttribute('key'):
    certKeysByIndex[index] = certElement.getAttribute('key')
    definedCertIndexesByName.setdefault(name, []).append(index)
   else:
    dependantCertElementsByIndex.setdefault(index, []).append(certElement)

 if packageName in packageElementsByName:
  packageElement = packageElementsByName[packageName]

  # Reset version in packages.xml
  packageElement.setAttribute('version', '0')

  # Replace certificate in packages.xml
  sigs = xml.createElement('sigs')
  sigs.setAttribute('count', '1')
  cert = xml.createElement('cert')
  cert.setAttribute('index', str(max(certKeysByIndex.keys()) + 1))
  cert.setAttribute('key', binascii.hexlify(certKey).decode('ascii'))
  sigs.appendChild(cert)
  packageElement.replaceChild(sigs, packageElement.getElementsByTagName('sigs')[0])

  # Re-insert deleted cert keys
  for idx in definedCertIndexesByName.get(packageName, []):
   for e in dependantCertElementsByIndex.get(idx, [])[:1]:
    e.setAttribute('key', certKeysByIndex[idx])

  return xml.toxml('utf-8')
