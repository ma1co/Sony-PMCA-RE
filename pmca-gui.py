#!/usr/bin/env python
"""A simple gui interface"""
import sys
from tkFileDialog import *
import traceback

import config
from pmca.commands.usb import *
from pmca.ui import *

if getattr(sys, 'frozen', False):
 from frozenversion import version
else:
 version = None

class PrintRedirector:
 """Redirect writes to a function"""
 def __init__(self, func, parent=None):
  self.func = func
  self.parent = parent
 def write(self, str):
  if self.parent:
   self.parent.write(str)
  self.func(str)


class InfoTask(BackgroundTask):
 """Task to run infoCommand()"""
 def doBefore(self):
  self.ui.infoButton.config(state=DISABLED)

 def do(self, arg):
  try:
   print ''
   infoCommand(config.appengineServer)
  except Exception:
   traceback.print_exc()

 def doAfter(self, result):
  self.ui.infoButton.config(state=NORMAL)


class InstallTask(BackgroundTask):
 """Task to run installCommand()"""
 def doBefore(self):
  self.ui.installButton.config(state=DISABLED)
  return self.ui.apkFile.get()

 def do(self, apkFilename):
  try:
   print ''
   if apkFilename:
    with open(apkFilename, 'rb') as f:
     installCommand(config.appengineServer, None, f)
   else:
    installCommand(config.appengineServer)
  except Exception:
   traceback.print_exc()

 def doAfter(self, result):
  self.ui.installButton.config(state=NORMAL)


class InstallerUi(UiRoot):
 """Main window"""
 def __init__(self, title):
  UiRoot.__init__(self)

  self.title(title)
  self.geometry('450x500')

  Grid.columnconfigure(self, 0, weight=1)
  Grid.rowconfigure(self, 3, weight=1)

  self.apkFile = Entry(self)
  self.apkFile.grid(row=0, column=0, sticky=W+E)

  self.apkSelectButton = Button(self, text='Open apk...', command=self.openApk)
  self.apkSelectButton.grid(row=0, column=1, sticky=W+E)

  self.infoButton = Button(self, text='Info', command=InfoTask(self).run)
  self.infoButton.grid(row=1, column=0, columnspan=2, sticky=W+E)

  self.installButton = Button(self, text='Install', command=InstallTask(self).run)
  self.installButton.grid(row=2, column=0, columnspan=2, sticky=W+E)

  self.logText = ScrollingText(self)
  self.logText.text.configure(state=DISABLED)
  self.logText.grid(row=3, column=0, columnspan=2, sticky=N+S+W+E)

  self.redirectStreams()

 def openApk(self):
  fn = askopenfilename(filetypes=[('Apk files', '.apk'), ('All files', '.*')])
  if fn:
   self.apkFile.delete(0, END)
   self.apkFile.insert(0, fn)

 def log(self, msg):
  self.logText.text.configure(state=NORMAL)
  self.logText.text.insert(END, msg)
  self.logText.text.configure(state=DISABLED)
  self.logText.text.see(END)

 def redirectStreams(self):
  for stream in ['stdout', 'stderr']:
   setattr(sys, stream, PrintRedirector(lambda str: self.run(lambda: self.log(str)), getattr(sys, stream)))


def main():
 """Gui main"""
 ui = InstallerUi('pmca-gui' + (' ' + version if version else ''))
 ui.mainloop()


if __name__ == '__main__':
 main()
