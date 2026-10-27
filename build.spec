# This file is used by other spec files

import os, shutil, subprocess, sys

excludes = ['bz2', 'cffi', 'Crypto', 'doctest', 'ftplib', 'gmpy', 'gmpy2', 'lzma', 'M2Crypto', 'numpy', 'py_compile', 'tack', 'tarfile', 'tracemalloc']
if sys.platform != 'darwin':
 # The macOS app bundle needs plistlib; other platforms keep upstream's exclude. pickle is
 # not excluded anywhere, since current PyInstaller's multiprocessing runtime hook needs it.
 excludes.append('plistlib')
if sys.platform != 'win32':
 excludes.append('pmca.usb.driver.windows')
if sys.platform != 'darwin':
 excludes.append('pmca.usb.driver.osx')

# Get version from git
try:
 version = subprocess.check_output(['git', 'describe', '--always', '--tags']).decode('ascii').strip()
except Exception:
 version = 'unknown'
with open('frozenversion.py', 'w') as f:
 f.write('version = "%s"' % version)

# Generate filename
suffix = {'linux2': '-linux', 'win32': '-win', 'darwin': '-macos'}
output += '-' + version + suffix.get(sys.platform, '')

# Analyze files
a = Analysis([input], excludes=excludes, datas=[('certs/*', 'certs')])
a.datas = [d for d in a.datas if not (d[0].startswith('certifi') and not d[0].endswith('cacert.pem'))]
a.datas += Tree('updatershell/fdat', 'updatershell/fdat')

pyz = PYZ(a.pure, a.zipped_data)

# Optional Developer ID signing (set CODESIGN_IDENTITY in the environment); ad-hoc otherwise
codesignIdentity = os.environ.get('CODESIGN_IDENTITY') or None
entitlements = 'entitlements.plist' if codesignIdentity else None

if sys.platform == 'darwin' and not console:
 # macOS app bundle: one-directory layout starts faster than a one-file executable
 # and is what Finder expects inside a .app
 exe = EXE(pyz, a.scripts, exclude_binaries=True, name=output, console=False, codesign_identity=codesignIdentity, entitlements_file=entitlements)
 coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name=output)
 app = BUNDLE(
  coll,
  name=output + '.app',
  codesign_identity=codesignIdentity,
  entitlements_file=entitlements,
  bundle_identifier='com.github.ma1co.openmemories.pmca-gui',
  info_plist={
   'CFBundleName': 'pmca-gui',
   'CFBundleDisplayName': 'pmca-gui',
   'CFBundleShortVersionString': version,
   'NSHighResolutionCapable': True,
   'LSMinimumSystemVersion': '11.0',
   'NSHumanReadableCopyright': 'OpenMemories',
  },
 )
 # Finder-friendly disk image containing the app and an Applications shortcut
 stage = os.path.join(DISTPATH, 'dmg')
 shutil.rmtree(stage, ignore_errors=True)
 os.makedirs(stage)
 shutil.copytree(app.name, os.path.join(stage, 'pmca-gui.app'), symlinks=True)
 os.symlink('/Applications', os.path.join(stage, 'Applications'))
 subprocess.check_call(['hdiutil', 'create', '-ov', '-quiet', '-volname', 'pmca-gui', '-fs', 'HFS+', '-srcfolder', stage, os.path.join(DISTPATH, output + '.dmg')])
 shutil.rmtree(stage)
 shutil.rmtree(os.path.join(DISTPATH, output))
else:
 # Single-file executable
 exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name=output, console=console, codesign_identity=codesignIdentity if sys.platform == 'darwin' else None, entitlements_file=entitlements if sys.platform == 'darwin' else None)

os.remove('frozenversion.py')
