# Modified from https://github.com/pyinstaller/pyinstaller/pull/2226

import os.path
import glob

from PyInstaller.compat import EXTENSION_SUFFIXES
from PyInstaller.utils.hooks import get_module_file_attribute

binaries = []
for mod in ['Crypto.Cipher', 'Crypto.Util', 'Crypto.Hash']:
 dir = os.path.dirname(get_module_file_attribute(mod))
 for ext in EXTENSION_SUFFIXES:
  for f in glob.glob(os.path.join(dir, '_*%s' % ext)):
   binaries.append((f, mod.replace('.', '/')))
