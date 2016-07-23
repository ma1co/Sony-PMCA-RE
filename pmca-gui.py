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


class AppLoadTask(BackgroundTask):
 def doBefore(self):
  self.ui.setAppList([])
  self.ui.appLoadButton.config(state=DISABLED)

 def do(self, arg):
  try:
   print ''
   return listApps(config.appengineServer)
  except Exception:
   traceback.print_exc()

 def doAfter(self, result):
  if result:
   self.ui.setAppList(result)
  self.ui.appLoadButton.config(state=NORMAL)


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
  return self.ui.getMode(), self.ui.getSelectedApk(), self.ui.getSelectedApp()

 def do(self, (mode, apkFilename, app)):
  try:
   print ''
   if mode == self.ui.MODE_APP and app:
    installCommand(config.appengineServer, None, None, app.package)
   elif mode == self.ui.MODE_APK and apkFilename:
    with open(apkFilename, 'rb') as f:
     installCommand(config.appengineServer, None, f)
   else:
    installCommand(config.appengineServer)
  except Exception:
   traceback.print_exc()

 def doAfter(self, result):
  self.ui.installButton.config(state=NORMAL)


class InstallerUi(UiRoot):
 MODE_APP = 0
 MODE_APK = 1

 """Main window"""
 def __init__(self, title):
  UiRoot.__init__(self)

  self.title(title)
  self.geometry('450x500')

  mainFrame = Frame(self, padding=10)
  mainFrame.pack(fill=X)

  self.modeVar = IntVar()
  self.modeVar.set(self.MODE_APP)

  appFrame = Labelframe(mainFrame, padding=5)
  appFrame['labelwidget'] = Radiobutton(appFrame, text='Select an app from the app list', variable=self.modeVar, value=self.MODE_APP)
  appFrame.pack(fill=X)

  self.appCombo = Combobox(appFrame, state='readonly')
  self.appCombo.bind('<<ComboboxSelected>>', lambda e: self.modeVar.set(self.MODE_APP))
  self.appCombo.pack(side=LEFT, fill=X, expand=True)
  self.setAppList([])

  self.appLoadButton = Button(appFrame, text='Refresh', command=AppLoadTask(self).run)
  self.appLoadButton.pack()

  apkFrame = Labelframe(mainFrame, padding=5)
  apkFrame['labelwidget'] = Radiobutton(apkFrame, text='Select an apk', variable=self.modeVar, value=self.MODE_APK)
  apkFrame.pack(fill=X)

  self.apkFile = Entry(apkFrame)
  self.apkFile.pack(side=LEFT, fill=X, expand=True)

  self.apkSelectButton = Button(apkFrame, text='Open apk...', command=self.openApk)
  self.apkSelectButton.pack()

  buttonFrame = Labelframe(mainFrame, padding=5)
  buttonFrame['labelwidget'] = Label(buttonFrame, text='Actions')
  buttonFrame.pack(fill=X)

  self.infoButton = Button(buttonFrame, text='Get camera info', command=InfoTask(self).run)
  self.infoButton.pack(fill=X)

  self.installButton = Button(buttonFrame, text='Install selected app', command=InstallTask(self).run)
  self.installButton.pack(fill=X)

  self.logText = ScrollingText(self)
  self.logText.text.configure(state=DISABLED)
  self.logText.pack(fill=BOTH, expand=True)

  self.redirectStreams()
  AppLoadTask(self).run()

 def getMode(self):
  return self.modeVar.get()

 def openApk(self):
  fn = askopenfilename(filetypes=[('Apk files', '.apk'), ('All files', '.*')])
  if fn:
   self.apkFile.delete(0, END)
   self.apkFile.insert(0, fn)
   self.modeVar.set(self.MODE_APK)

 def getSelectedApk(self):
  return self.apkFile.get()

 def log(self, msg):
  self.logText.text.configure(state=NORMAL)
  self.logText.text.insert(END, msg)
  self.logText.text.configure(state=DISABLED)
  self.logText.text.see(END)

 def redirectStreams(self):
  for stream in ['stdout', 'stderr']:
   setattr(sys, stream, PrintRedirector(lambda str: self.run(lambda: self.log(str)), getattr(sys, stream)))

 def setAppList(self, apps):
  self.appList = apps
  self.appCombo['values'] = [''] + [app.name for app in apps]
  self.appCombo.current(0)

 def getSelectedApp(self):
  if self.appCombo.current() > 0:
   return self.appList[self.appCombo.current() - 1]


def main():
 """Gui main"""
 ui = InstallerUi('pmca-gui' + (' ' + version if version else ''))
 ui.mainloop()


if __name__ == '__main__':
 main()
