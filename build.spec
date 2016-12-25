# This file is used by other spec files

import os, shutil, subprocess, sys

excludes = ['encodings.bz2_codec', 'encodings.idna', 'Crypto.Cipher._DES', 'Crypto.Cipher._DES3', 'Crypto.Hash._SHA256', 'numpy']

# Get version from git
version = subprocess.check_output(['git', 'describe', '--always', '--tags']).decode('ascii').strip()
with open('frozenversion.py', 'w') as f:
 f.write('version = "%s"' % version)

# Generate filename
suffix = {'linux2': '-linux', 'win32': '-win', 'darwin': '-osx'}
output += '-' + version + suffix.get(sys.platform, '')

# Analyze files
a = Analysis([input], excludes=excludes, datas=[('certs/*', 'certs')], hookspath=['hooks'])
a.binaries = [((os.path.basename(name) if type == 'BINARY' else name), path, type) for name, path, type in a.binaries]# libusb binaries are not found in subdirs
a.datas = [d for d in a.datas if not (d[0].startswith('certifi') and not d[0].endswith('cacert.pem'))]

# Generate executable
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name=output, console=console)
if sys.platform == 'darwin' and not console:
 app = BUNDLE(exe, name=output+'.app')
 os.remove(exe.name)
 subprocess.check_call(['hdiutil', 'create', DISTPATH+'/'+output+'.dmg', '-srcfolder', app.name])
 shutil.rmtree(app.name)

os.remove('frozenversion.py')
