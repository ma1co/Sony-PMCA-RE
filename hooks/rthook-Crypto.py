# Runtime hook for pycryptodome extensions

import Crypto.Util._raw_api
import importlib.machinery
import os.path
import sys

def load_raw_lib(name, cdecl):
 for ext in importlib.machinery.EXTENSION_SUFFIXES:
  try:
   return Crypto.Util._raw_api.load_lib(os.path.join(sys._MEIPASS, name + ext), cdecl)
  except OSError:
   pass

Crypto.Util._raw_api.load_pycryptodome_raw_lib = load_raw_lib
