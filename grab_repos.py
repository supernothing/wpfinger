#!/usr/bin/env python
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

import os
import sys
import thread
import time
from pipes import quote

from theme_repos import data
from parallel import get_threads
from repo_names import get_names

def f(cur,kw):
    '''
        Does checkout. Yes, shouldn't use os.system. Next version.
    '''
    i = 0
    while i < 5:
        res = os.system("svn co %s %s" % (quote(kw['url'] + cur),
                quote(os.path.join(kw['base'],cur))))
        if res == 0:
            break
        i+=1
        time.sleep(5)
        print "Error occurred downloading repo. Waiting 5 seconds..."
    if res != 0:
        print "Error occured. Exiting thread..."
        sys.exit(0)

def checkout_repos(url,base,threads=20):
    gen = iter(get_names(url))
    threads,out = get_threads(gen,f,threads,
            url=url,base=base)
    for t in threads:
        t.join()
    print "done"

def checkout_themes(base,threads=20):
    return checkout_repos("http://themes.svn.wordpress.org/",base)

def checkout_plugins(base,threads=20):
    return checkout_repos("http://plugins.svn.wordpress.org/",base)

if __name__=="__main__":
    checkout_plugins("wordpress_plugins")
    checkout_themes("wordpress_themes")
