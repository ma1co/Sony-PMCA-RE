from ..backup import *

def printHexDump(data, n=16, indent=0):
 for i in range(0, len(data), n):
  line = bytearray(data[i:i+n])
  hex = ' '.join('%02x' % c for c in line)
  text = ''.join(chr(c) if 0x21 <= c <= 0x7e else '.' for c in line)
  print('%*s%-*s %s' % (indent, '', n*3, hex, text))

def printBackupCommand(file):
 """Prints all properties in a Backup.bin file"""
 for id, property in BackupFile(file).listProperties():
  print('id=0x%08x, size=0x%04x, attr=0x%02x:' % (id, len(property.data), property.attr))
  printHexDump(property.data, indent=2)
  if property.resetData and property.resetData != property.data:
   print('reset data:')
   printHexDump(property.resetData, indent=2)
  print('')
