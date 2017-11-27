import re

class ArgParser:
 def __init__(self, str):
  self.str = str
  self._consumeWhitespace()

 def _match(self, r):
  return re.match(r, self.str)

 def _consume(self, r):
  m = self._match(r)
  if m:
   self.str = self.str[len(m.group(0)):]
   return m

 def _consumeWhitespace(self):
  m = self._consume('\s+')
  if m:
   return m.group(0)

 def _consumeEscaped(self, char):
  m = self._consume('%c(([^%c\\\\]|\\\\.)*)%c' % (3 * (char,)))
  if m:
   return m.group(1)

 def _consumeSingleQuoted(self):
  return self._consumeEscaped('\'')

 def _consumeDoubleQuoted(self):
  return self._consumeEscaped('"')

 def _consumeUnquoted(self):
  m = self._consume('([^\s"\'\\\\]|\\\\[^\s])*(\\\\(?=(\s|$)))?')
  if m and m.group(0) != '':
   return m.group(0)

 def _unescape(self, str):
  return re.sub('\\\\([\\\\"\'])', '\\1', str)

 def available(self):
  return self.str != ''

 def _consumeArg(self):
  arg = ''
  while self.available() and not self._match('\s'):
   for f in [self._consumeSingleQuoted, self._consumeDoubleQuoted, self._consumeUnquoted]:
    a = f()
    if a is not None:
     arg += self._unescape(a)
     break
   else:
    raise ValueError("Cannot match quotes")
  self._consumeWhitespace()
  return arg

 def consumeRequiredArg(self):
  if not self.available():
   raise ValueError("Not enough arguments provided")
  return self._consumeArg()

 def consumeOptArg(self, default=None):
  return self._consumeArg() if self.available() else default

 def consumeArgs(self, nRequired=0, nOpt=0, optDefaults=[]):
  args = [self.consumeRequiredArg() for i in range(nRequired)]
  args += [self.consumeOptArg(optDefaults[i] if i < len(optDefaults) else None) for i in range(nOpt)]
  if self.available():
   raise ValueError("Too many arguments provided")
  return args

 def getResidue(self):
  return self.str
