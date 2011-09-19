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


import urllib2

from parallel import get_threads
from repo_names import get_names
import time

def do_request(url,retries=5):
    i = 0
    while i < retries:
        try:
            return  urllib2.urlopen(url)
        except:
            i+=1
            time.sleep(5)
            print "Error occurred grabbing page. Waiting 5 seconds..."
            continue
    return None

def f_plugin(cur,kw):
    url = "http://wordpress.org/extend/plugins/%s/" % cur
    res = do_request(url)
    if res == None:
        print "Connection to server failed on plugin %s, stats might be bad." % cur
    if res.geturl() == url:
        data = res.read()
        start = data.find("Downloads:</strong>")+len("Downloads:</strong>")
        end = data.find("<",start)
        count = data[start:end].strip().replace(",","")
        if count.find("Transitional") == -1:
            print "%s:%s" %(cur,count)
            return (int(count),cur)
        else:
            print "Finding stats for %s failed, probably no longer exists." % cur

def f_theme(cur,kw):
    url = "http://wordpress.org/extend/themes/%s/stats/" % cur
    res = do_request(url)
    if res == None:
        print "Connection to server failed on plugin %s, stats might be bad." % cur
    if res.geturl() == url:
        data = res.read()
        start = data.find("td",data.find('<th scope="row">All Time</th>'))+len("<td>")-1
        end = data.find("<",start)
        count = data[start:end].strip().replace(",","")
        if count.find("OCTYP") == -1:
            print "%s:%s" %(cur,count)
            return (int(count),cur)
        else:
            print "Finding stats for %s failed, probably no longer exists." % cur

def get_theme_stats(threads=20):
    gen = iter(get_names("http://themes.svn.wordpress.org"))
    threads,out = get_threads(gen,f_theme,threads)
    for t in threads:
        t.join()
    return out
def get_plugin_stats(threads=20):
    gen = iter(get_names("http://plugins.svn.wordpress.org"))
    threads,out = get_threads(gen,f_plugin,threads)
    for t in threads:
        t.join()
    return out


def main():
    res = get_plugin_stats()
    res.sort(reverse=True)
    f = open("plugin_stats.txt","w")
    for p in res:
        f.write("%s %s\n" % p)

    res = get_theme_stats()
    res.sort(reverse=True)
    f = open("theme_stats.txt","w")
    for p in res:
        f.write("%s %s\n" % p)

if __name__=="__main__":
    main()
