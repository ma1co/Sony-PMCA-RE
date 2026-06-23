"""Gui related classes"""

import sys
import threading
from queue import Queue, Empty
from tkinter import *
from tkinter.ttk import *
from tkinter.filedialog import askopenfilename
from tkinter.simpledialog import Dialog


def configureModernMacTk(root):
 """Prefer a light Tk theme on macOS."""
 if sys.platform != 'darwin':
  return

 try:
  style = Style(root)
  if 'clam' in style.theme_names():
   style.theme_use('clam')

  colors = {
   'window': '#f5f5f5',
   'panel': '#ffffff',
   'border': '#c8c8c8',
   'text': '#111111',
   'selected': '#d8e8ff',
  }

  root.configure(background=colors['window'])

  style.configure('.', background=colors['window'], foreground=colors['text'])
  style.configure('TFrame', background=colors['window'])
  style.configure('TLabel', background=colors['window'], foreground=colors['text'])
  style.configure('TButton', background=colors['panel'], foreground=colors['text'])
  style.configure('TCheckbutton', background=colors['window'], foreground=colors['text'])
  style.configure('TRadiobutton', background=colors['window'], foreground=colors['text'])
  style.configure('TLabelframe', background=colors['window'], bordercolor=colors['border'])
  style.configure('TLabelframe.Label', background=colors['window'], foreground=colors['text'])
  style.configure('TNotebook', background=colors['window'], borderwidth=0)
  style.configure('TNotebook.Tab', background='#e8e8e8', foreground=colors['text'], padding=(8, 4))
  style.map('TNotebook.Tab',
            background=[('selected', colors['panel'])],
            foreground=[('selected', colors['text'])])
  style.configure('TEntry', fieldbackground=colors['panel'], foreground=colors['text'])
  style.configure('TCombobox',
                  fieldbackground=colors['panel'],
                  background=colors['panel'],
                  foreground=colors['text'],
                  arrowcolor=colors['text'])
  style.map('TCombobox',
            fieldbackground=[('readonly', colors['panel'])],
            selectbackground=[('readonly', colors['selected'])],
            selectforeground=[('readonly', colors['text'])])
 except Exception:
  pass

class UiRoot(Tk):
 def __init__(self):
  Tk.__init__(self)
  configureModernMacTk(self)
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
  parent = self.master
  while parent and not hasattr(parent, 'run'):
   parent = parent.master
  if parent:
   parent.run(func)


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
  self.text = Text(self, wrap=WORD, yscrollcommand=self.scrollbar.set)
  self.text.grid(row=0, column=0, sticky=N+S+W+E)
  self.scrollbar.config(command=self.text.yview)
