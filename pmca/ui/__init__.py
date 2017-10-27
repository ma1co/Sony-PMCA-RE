"""Gui related classes"""

import sys
import threading

try:
 from queue import Queue, Empty
except ImportError:
 # Python 2
 from Queue import Queue, Empty

if sys.version_info >= (3,):
 from tkinter import *
 from tkinter.ttk import *
 from tkinter.filedialog import askopenfilename
 from tkinter.simpledialog import Dialog
else:
 # Python 2
 from Tkinter import *
 from ttk import *
 from tkFileDialog import askopenfilename
 from tkSimpleDialog import Dialog

class UiRoot(Tk):
 def __init__(self):
  Tk.__init__(self)
  self._queue = Queue()
  self._processQueue()

 def run(self, func):
  """Post functions to run them on the main thread"""
  self._queue.put(func)

 def _processQueue(self):
  while True:
   try:
    self._queue.get(block=False)()
   except Empty:
    break
  self.after(100, self._processQueue)


class UiFrame(Frame):
 def run(self, func):
  self.master.run(func)


class UiDialog(Dialog):
 def run(self, func):
  self.master.run(func)

 def buttonbox(self):
  pass


class BackgroundTask(object):
 """Similar to Android's AsyncTask"""
 def __init__(self, ui):
  self.ui = ui

 def doBefore(self):
  """Runs on the main thread, returns arg"""
  pass
 def do(self, arg):
  """Runs on a separate thread, returns result"""
  pass
 def doAfter(self, result):
  """Runs on the main thread again"""
  pass

 def run(self):
  """Invoke this on the main thread only"""
  arg = self.doBefore()
  threading.Thread(target=self._onThread, args=[arg]).start()

 def _onThread(self, arg):
  result = self.do(arg)
  self.ui.run(lambda: self.doAfter(result))


class ScrollingText(Frame):
 """A wrapper for a Text widget with a scrollbar"""
 def __init__(self, parent):
  Frame.__init__(self, parent)
  Grid.columnconfigure(self, 0, weight=1)
  Grid.rowconfigure(self, 0, weight=1)
  self.scrollbar = Scrollbar(self)
  self.scrollbar.grid(row=0, column=1, sticky=N+S)
  self.text = Text(self, yscrollcommand=self.scrollbar.set)
  self.text.grid(row=0, column=0, sticky=N+S+W+E)
  self.scrollbar.config(command=self.text.yview)
