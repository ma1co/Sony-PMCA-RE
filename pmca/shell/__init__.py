import abc
from collections import OrderedDict
import sys

from .parser import *

if sys.version_info < (3,):
 # Python 2
 input = raw_input


class BaseCommand(abc.ABC):
 @abc.abstractmethod
 def help(self):
  pass

 @abc.abstractmethod
 def run(self, parser):
  pass


class SubCommand(BaseCommand):
 def __init__(self):
  self._commands = OrderedDict()

 def addCommand(self, name, cmd):
  self._commands[name] = cmd

 def help(self, path=''):
  return '\n'.join(cmd.help('%s %s' % (path, name)) for name, cmd in self._commands.items())

 def run(self, parser):
  name = parser.consumeRequiredArg()
  if name not in self._commands:
   raise Exception('Unknown command')
  self._commands[name].run(parser)


class Command(BaseCommand):
 def __init__(self, func, args, help, argHelp=''):
  self._func = func
  self._args = args
  self._help = help
  self._argHelp = argHelp

 def help(self, path):
  return '%-24s %s' % ('%s %s' % (path, self._argHelp), self._help)

 def run(self, parser):
  self._func(*parser.consumeArgs(*self._args))


class ResidueCommand(Command):
 def run(self, parser):
  self._func(*[parser.consumeRequiredArg() for i in range(self._args)], parser.getResidue())


class Shell:
 def __init__(self, name):
  self.name = name
  self.running = False
  self.commands = SubCommand()

  self.addCommand('help', Command(self.help, (), 'Print this help message'))
  self.addCommand('exit', Command(self.exit, (), 'Exit'))

 def addCommand(self, name, cmd):
  self.commands.addCommand(name, cmd)

 def run(self):
  print('Welcome to %s.' % self.name)
  print('Type `help` for the list of supported commands.')
  print('Type `exit` to quit.')

  self.running = True
  while self.running:
   try:
    cmd = input('>').strip()
   except KeyboardInterrupt:
    print('')
    continue

   try:
    parser = ArgParser(cmd)
    if not parser.available():
     continue
    self.commands.run(parser)
   except Exception as e:
    print('Error: %s' % e)

 def help(self):
  print('List of supported commands:')
  print(self.commands.help())

 def exit(self):
  self.running = False
