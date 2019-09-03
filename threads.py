__filename__ = "threads.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import threading
import sys
import trace
import time

class threadWithTrace(threading.Thread): 
    def __init__(self, *args, **keywords):
        self._args, self._keywords = args, keywords
        threading.Thread.__init__(self, *self._args, **self._keywords) 
        self.killed = False
  
    def start(self): 
        self.__run_backup = self.run 
        self.run = self.__run       
        threading.Thread.start(self) 
  
    def __run(self): 
        sys.settrace(self.globaltrace) 
        self.__run_backup() 
        self.run = self.__run_backup 
  
    def globaltrace(self, frame, event, arg): 
        if event == 'call': 
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, event, arg): 
        if self.killed: 
            if event == 'line': 
                raise SystemExit() 
        return self.localtrace 
  
    def kill(self): 
        self.killed = True

    def clone(self):
        return threadWithTrace(target=self, \
                               args=(self._args),daemon=True)        
