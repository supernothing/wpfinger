'''
This is an alpha implementation of a Wordpress plugin fingerprinting toolkit.
It uses makeshift binary search trees created by diffing SVN repository info
to determine not only if a plugin is installed

Copyright 2011, Ben Schmidt
Released under the GPL v3
'''

__author__ = "Ben Schmidt"
__copyright__ = "Copyright 2011, Ben Schmidt"
__credits__ = ["Ben Schmidt"]
__license__ = "GPL v3"
__version__ = "0.1"
__maintainer__ = "Ben Schmidt"
__email__ = "supernothing@spareclockcycles.org"
__status__ = "alpha"

import threading

class LockedIterator(object):
    def __init__(self, it):
        self.lock = threading.Lock()
        self.it = it.__iter__()

    def __iter__(self): return self

    def next(self):
        self.lock.acquire()
        try:
            return self.it.next()
        finally:
            self.lock.release()

class Parallel(threading.Thread):
    '''
        Crappy generic-ish thread for my common uses.
    '''
    def __init__(self,func,g,out,keywords):
        self.g = g
        self.func = func
        self.out = out
        self.kw = keywords
        threading.Thread.__init__(self)
    def run(self):
        while 1:
            try:
                res = self.func(self.g.next(),self.kw)
                if res != None:
                    self.out.append(res)
            except StopIteration:
                break

def get_threads(g,f,num,**keywords):
    gen = LockedIterator(g)
    threads,out = [],[]
    for i in xrange(0,num):
        threads.append(Parallel(f,g,out,keywords))
        threads[-1].start()
    return threads,out
