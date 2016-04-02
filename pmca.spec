# Run `pyinstaller pmca.spec` to generate an executable

import os.path, subprocess, sys

# Generate filename
suffix = {'linux2': '-linux', 'win32': '-win', 'darwin': '-osx'}
output = 'pmca-' + subprocess.check_output(['git', 'describe', '--always', '--tags']).strip() + suffix.get(sys.platform, '')

# Analyze files
a = Analysis(['pmca.py'], excludes=['numpy'], datas=[('certs/*', 'certs')])# Don't let comtypes include numpy
a.binaries = [((os.path.basename(name) if type == 'BINARY' else name), path, type) for name, path, type in a.binaries]# libusb binaries are not found in subdirs

# Generate executable
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name=output)
