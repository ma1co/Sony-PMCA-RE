# This file is used by other spec files

import os, shutil, subprocess, sys

excludes = ['apkutils.cert', 'bz2', 'cffi', 'Crypto', 'doctest', 'ftplib', 'lzma', 'numpy', 'pickle', 'plistlib', 'py_compile', 'tarfile', 'tracemalloc']
if sys.platform != 'win32':
 excludes.append('pmca.usb.driver.windows')
if sys.platform != 'darwin':
 excludes.append('pmca.usb.driver.osx')

# Get version from git
version = subprocess.check_output(['git', 'describe', '--always', '--tags']).decode('ascii').strip()
with open('frozenversion.py', 'w') as f:
 f.write('version = "%s"' % version)

# Generate filename
suffix = {'linux2': '-linux', 'win32': '-win', 'darwin': '-osx'}
output += '-' + version + suffix.get(sys.platform, '')

# Analyze files
a = Analysis([input], excludes=excludes, datas=[('certs/*', 'certs')])
a.datas = [d for d in a.datas if not (d[0].startswith('certifi') and not d[0].endswith('cacert.pem'))]
a.datas += Tree('updatershell/fdat', 'updatershell/fdat')

# Generate executable
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name=output, console=console)
if sys.platform == 'darwin' and not console:
 app = BUNDLE(exe, name=output+'.app')
 os.remove(exe.name)
 subprocess.check_call(['hdiutil', 'create', '-ov', DISTPATH+'/'+output+'.dmg', '-srcfolder', app.name])
 shutil.rmtree(app.name)

os.remove('frozenversion.py')
