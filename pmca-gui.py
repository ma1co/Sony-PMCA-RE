#!/usr/bin/env python3
"""A simple gui interface"""
from __future__ import print_function
import sys
import traceback
import webbrowser

import config
from pmca.commands.usb import *
from pmca.ui import *
from pmca.usb.usbshell import *

if getattr(sys, 'frozen', False):
 from frozenversion import version
else:
 version = None

class PrintRedirector(object):
 """Redirect writes to a function"""
 def __init__(self, func, parent=None):
  self.func = func
  self.parent = parent
 def write(self, str):
  if self.parent:
   self.parent.write(str)
  self.func(str)
 def flush(self):
  self.parent.flush()


class AppLoadTask(BackgroundTask):
 def doBefore(self):
  self.ui.setAppList([])
  self.ui.appLoadButton.config(state=DISABLED)

 def do(self, arg):
  try:
   print('')
   return list(listApps().values())
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
   print('')
   infoCommand()
  except Exception:
   traceback.print_exc()

 def doAfter(self, result):
  self.ui.infoButton.config(state=NORMAL)


class InstallTask(BackgroundTask):
 """Task to run installCommand()"""
 def doBefore(self):
  self.ui.installButton.config(state=DISABLED)
  return self.ui.getMode(), self.ui.getSelectedApk(), self.ui.getSelectedApp()

 def do(self, args):
  (mode, apkFilename, app) = args
  try:
   print('')
   if mode == self.ui.MODE_APP and app:
    installCommand(appPackage=app.package)
   elif mode == self.ui.MODE_APK and apkFilename:
    with open(apkFilename, 'rb') as f:
     installCommand(apkFile=f)
   else:
    installCommand()
  except Exception:
   traceback.print_exc()

 def doAfter(self, result):
  self.ui.installButton.config(state=NORMAL)


class FirmwareUpdateTask(BackgroundTask):
 """Task to run firmwareUpdateCommand()"""
 def doBefore(self):
  self.ui.fwUpdateButton.config(state=DISABLED)
  return self.ui.getSelectedDat()

 def do(self, datFile):
  try:
   if datFile:
    print('')
    with open(datFile, 'rb') as f:
     firmwareUpdateCommand(f)
  except Exception:
   traceback.print_exc()

 def doAfter(self, result):
  self.ui.fwUpdateButton.config(state=NORMAL)


class StartUpdaterShellTask(BackgroundTask):
 """Task to run updaterShellCommand() and open UpdaterShellDialog"""
 def doBefore(self):
  self.ui.startButton.config(state=DISABLED)

 def do(self, arg):
  try:
   print('')
   updaterShellCommand(complete=self.launchShell)
  except Exception:
   traceback.print_exc()

 def launchShell(self, dev):
  shell = UsbShell(dev)
  shell.waitReady()

  endFlag = threading.Event()
  root = self.ui.master
  root.run(lambda: root.after(0, lambda: UpdaterShellDialog(root, shell, endFlag)))
  endFlag.wait()

  try:
   shell.syncBackup()
  except:
   print('Cannot sync backup')
  shell.exit()

 def doAfter(self, result):
  self.ui.startButton.config(state=NORMAL)


class TweakStatusTask(BackgroundTask):
 """Task to run UsbShell.getTweakStatus()"""
 def doBefore(self):
  self.ui.setState(DISABLED)

 def do(self, arg):
  try:
   return list(self.ui.shell.getTweakStatus())
  except Exception:
   traceback.print_exc()

 def doAfter(self, result):
  self.ui.setState(NORMAL)
  self.ui.setTweakStatus(result)


class TweakSetTask(BackgroundTask):
 """Task to run UsbShell.setTweakEnabled()"""
 def __init__(self, ui, id, var):
  BackgroundTask.__init__(self, ui)
  self.id = id
  self.var = var

 def doBefore(self):
  self.ui.setState(DISABLED)
  return self.var.get()

 def do(self, arg):
  try:
   self.ui.shell.setTweakEnabled(self.id, arg)
  except Exception:
   traceback.print_exc()

 def doAfter(self, result):
  self.ui.setState(NORMAL)
  self.ui.updateStatus()


class InstallerUi(UiRoot):
 """Main window"""
 def __init__(self, title):
  UiRoot.__init__(self)

  self.title(title)
  self.geometry('450x500')
  self['menu'] = Menu(self)

  tabs = Notebook(self, padding=5)
  tabs.pack(fill=X)

  tabs.add(InfoFrame(self, padding=10), text='Camera info')
  tabs.add(InstallerFrame(self, padding=10), text='Install app')
  tabs.add(UpdaterShellFrame(self, padding=10), text='Tweaks')
  tabs.add(FirmwareFrame(self, padding=10), text='Update firmware')

  self.logText = ScrollingText(self)
  self.logText.text.configure(state=DISABLED)
  self.logText.pack(fill=BOTH, expand=True)

  self.redirectStreams()

 def log(self, msg):
  self.logText.text.configure(state=NORMAL)
  self.logText.text.insert(END, msg)
  self.logText.text.configure(state=DISABLED)
  self.logText.text.see(END)

 def redirectStreams(self):
  for stream in ['stdout', 'stderr']:
   setattr(sys, stream, PrintRedirector(lambda str: self.run(lambda: self.log(str)), getattr(sys, stream)))


class InfoFrame(UiFrame):
 def __init__(self, parent, **kwargs):
  UiFrame.__init__(self, parent, **kwargs)

  self.infoButton = Button(self, text='Get camera info', command=InfoTask(self).run, padding=5)
  self.infoButton.pack(fill=X)


class InstallerFrame(UiFrame):
 MODE_APP = 0
 MODE_APK = 1

 def __init__(self, parent, **kwargs):
  UiFrame.__init__(self, parent, **kwargs)

  self.modeVar = IntVar(value=self.MODE_APP)

  appFrame = Labelframe(self, padding=5)
  appFrame['labelwidget'] = Radiobutton(appFrame, text='Select an app from the app list', variable=self.modeVar, value=self.MODE_APP)
  appFrame.columnconfigure(0, weight=1)
  appFrame.pack(fill=X)

  self.appCombo = Combobox(appFrame, state='readonly')
  self.appCombo.bind('<<ComboboxSelected>>', lambda e: self.modeVar.set(self.MODE_APP))
  self.appCombo.grid(row=0, column=0, sticky=W+E)
  self.setAppList([])

  self.appLoadButton = Button(appFrame, text='Refresh', command=AppLoadTask(self).run)
  self.appLoadButton.grid(row=0, column=1)

  appListLink = Label(appFrame, text='Source', foreground='blue', cursor='hand2')
  appListLink.bind('<Button-1>', lambda e: webbrowser.open_new('https://' + config.appengineServer + '/apps'))
  appListLink.grid(columnspan=2, sticky=W)

  apkFrame = Labelframe(self, padding=5)
  apkFrame['labelwidget'] = Radiobutton(apkFrame, text='Select an apk', variable=self.modeVar, value=self.MODE_APK)
  apkFrame.columnconfigure(0, weight=1)
  apkFrame.pack(fill=X)

  self.apkFile = Entry(apkFrame)
  self.apkFile.grid(row=0, column=0, sticky=W+E)

  self.apkSelectButton = Button(apkFrame, text='Open apk...', command=self.openApk)
  self.apkSelectButton.grid(row=0, column=1)

  self.installButton = Button(self, text='Install selected app', command=InstallTask(self).run, padding=5)
  self.installButton.pack(fill=X, pady=(5, 0))

  self.run(AppLoadTask(self).run)

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

 def setAppList(self, apps):
  self.appList = apps
  self.appCombo['values'] = [''] + [app.name for app in apps]
  self.appCombo.current(0)

 def getSelectedApp(self):
  if self.appCombo.current() > 0:
   return self.appList[self.appCombo.current() - 1]


class FirmwareFrame(UiFrame):
 def __init__(self, parent, **kwargs):
  UiFrame.__init__(self, parent, **kwargs)

  datFrame = Labelframe(self, padding=5)
  datFrame['labelwidget'] = Label(datFrame, text='Firmware file')
  datFrame.pack(fill=X)

  self.datFile = Entry(datFrame)
  self.datFile.pack(side=LEFT, fill=X, expand=True)

  self.datSelectButton = Button(datFrame, text='Open...', command=self.openDat)
  self.datSelectButton.pack()

  self.fwUpdateButton = Button(self, text='Update firmware', command=FirmwareUpdateTask(self).run, padding=5)
  self.fwUpdateButton.pack(fill=X, pady=(5, 0))

 def openDat(self):
  fn = askopenfilename(filetypes=[('Firmware files', '.dat'), ('All files', '.*')])
  if fn:
   self.datFile.delete(0, END)
   self.datFile.insert(0, fn)

 def getSelectedDat(self):
  return self.datFile.get()


class UpdaterShellFrame(UiFrame):
 def __init__(self, parent, **kwargs):
  UiFrame.__init__(self, parent, **kwargs)

  self.startButton = Button(self, text='Start tweaking (updater mode)', command=StartUpdaterShellTask(self).run, padding=5)
  self.startButton.pack(fill=X)


class UpdaterShellDialog(UiDialog):
 def __init__(self, parent, shell, endFlag=None):
  self.shell = shell
  self.endFlag = endFlag
  UiDialog.__init__(self, parent, "Updater mode tweaks")

 def body(self, top):
  tweakFrame = Labelframe(top, padding=5)
  tweakFrame['labelwidget'] = Label(tweakFrame, text='Tweaks')
  tweakFrame.pack(fill=X)

  self.boxFrame = Frame(tweakFrame)
  self.boxFrame.pack(fill=BOTH, expand=True)

  self.doneButton = Button(top, text='Done', command=self.cancel, padding=5)
  self.doneButton.pack(fill=X)

  self.updateStatus()

 def updateStatus(self):
  TweakStatusTask(self).run()

 def setTweakStatus(self, tweaks):
  for child in self.boxFrame.winfo_children():
   child.destroy()
  if tweaks:
   for id, desc, status, value in tweaks:
    var = IntVar(value=status)
    c = Checkbutton(self.boxFrame, text=desc + '\n' + value, variable=var, command=TweakSetTask(self, id, var).run)
    c.pack(fill=X)
  else:
   Label(self.boxFrame, text='No tweaks available').pack(fill=X)

 def setState(self, state):
  for widget in self.boxFrame.winfo_children() + [self.doneButton]:
   widget.config(state=state)

 def cancel(self, event=None):
  UiDialog.cancel(self, event)
  if self.endFlag:
   self.endFlag.set()


def main():
 """Gui main"""
 ui = InstallerUi('pmca-gui' + (' ' + version if version else ''))
 ui.mainloop()


if __name__ == '__main__':
 main()
