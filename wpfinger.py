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
import hashlib
import httplib
from urlparse import urlparse
import types
import random
import string
import difflib
import optparse

from parallel import get_threads

hashable_filetypes = ["css","js","swf","xml","htm","html","png","jpg","jpeg","gif","txt"]
presence_filetypes = ["css","js","swf","xml","htm","html","png","jpg","jpeg","gif","txt","php","mo","po"]

def build_detection(vers,fl,hs):
    '''
        This uses file presence and then content to build a makeshift
        binary search tree, which we can then use to fingerprint a target.
    '''
    if len(vers) <= 1:
        return ('', vers[0] if len(vers) > 0 else '')
    sig = fl[vers[0]].symmetric_difference(fl[vers[-1]])
    lsig = list(sig)
    if len(sig) > 0:
        if len(vers) > 2:
            return (lsig[0]+":"+('0' if lsig[0] in fl[vers[0]] else '1'),
                build_detection(vers[0:len(vers)/2],fl,hs),
                build_detection(vers[len(vers)/2+1:len(vers)],fl,hs))
        else:
            return (lsig[0]+":"+('0' if lsig[0] in fl[vers[0]] else '1'),
                    vers[0],vers[-1])
    else:
        sig = hs[vers[0]].symmetric_difference(hs[vers[-1]])
        lsig = list(sig)
        if len(sig) > 0:
            if len(vers) > 2:
                return (lsig[0]+":"+('0' if lsig[0] in hs[vers[0]] else '1'),
                    build_detection(vers[0:len(vers)/2],fl,hs),
                    build_detection(vers[len(vers)/2+1:len(vers)],fl,hs))
            else:
                return (lsig[0]+":"+('0' if lsig[0] in hs[vers[0]] else '1'),
                        vers[0],vers[-1])
        return ("",vers[0],vers[-1])

def generate_fingerprint(path):
    '''
        Generate a fingerprint given a Wordpress plugin repo
    '''
    hashes = {}
    filelists = {}
    ver = ""
   
    '''
    For future
    versions = [os.path.join(path,n) for n in os.path.join(os.listdir(path),"tags")
                    if os.path.isdir(os.path.join(path,n)]+["trunk"]
    '''
    #build our filelists for each version
    
    for cur in os.walk(path):
        temp = cur[0].split("/")
        cur[1].remove(".svn")
        if temp[-1] == "tags":
            if len(cur[1])>1:
                ver = cur[1][0]
            else:
                ver = "trunk"
            hashes[ver] = []
            filelists[ver] = []
            continue
        if ver != "":
            if ver not in temp:
                ver = temp[-1]
                hashes[ver] = []
                filelists[ver] = []
            lpath = "/".join(temp[temp.index(ver)+1:])
            new_files = [os.path.join(lpath,f) for f in cur[2] 
                    if f.split(".")[-1] in presence_filetypes]
            for f in new_files:
                if f.split(".")[-1] in hashable_filetypes:
                    h = hashlib.md5(open(os.path.join(cur[0],f.split("/")[-1])).read())
                    hashes[ver].append("%s:%s" % (f,h.hexdigest()))
            filelists[ver].extend(new_files)
    
    for ver in filelists:
        filelists[ver] = set(filelists[ver])
        hashes[ver] = set(hashes[ver])
    identify = list(reduce(lambda x,y: x&y,filelists.values()))
    vers = filelists.keys()
    vers.sort()
    sigs = build_detection(vers,filelists,hashes)
    if len(identify) == 0:
        #assumes that 3 files should cover bases
        identify = [sigs[0].split(":")[0],sigs[1][0].split(":")[0],
                    sigs[2][0].split(":")[0]]
    else:
        identify = [identify[0]]
    print (identify,sigs)
    return (identify,sigs)

def fingerprint_plugins(base="wordpress_plugins",pstats="plugin_stats.txt",limit=-1):
    plugins = [p.strip().split()[1] for p in open("plugin_stats.txt").readlines()]
    if limit == -1:
        limit = len(plugins)
    i = 0
    sigs = {}
    while i < limit:
        try:
            sigs[plugins[i]] = generate_fingerprint(os.path.join(base,plugins[i]))
        except:
            print "Failed to fingerprint %s" % plugins[i]
        i+=1
    return sigs

def do_request(target,path,retries=5):
    i = 0
    while i < retries:
        try:
            con = httplib.HTTPConnection(target)
            con.request("GET",path)
            return con.getresponse()
        except:
            i+=1
            continue
    return None

def finger(cur,kw):
    '''
        This is the code that gets run in the threads,
        and actually performs the fingerprinting.
    '''
    target = kw['target']
    base = target.path
    default_code = kw['default_code']
    default_data = kw['default_data']
    disable_dirmatch = kw['disable_dirmatch']
    if cur not in sigs:
        return
    if base.endswith("/"):
        base += "wp-content/plugins/"
    else: 
        base += "/wp-content/plugins/"
    success = False
    for path in sigs[cur][0]:
        if path.endswith("index.php"):
            path = path.replace("index.php","")
        if path.find(".") == -1:
            #wtf, workaround for bug in signatures to avoid false positives
            path = ""
        #Here we try one or more paths that should identify
        #an installation even if directories are locked down
        res = do_request(target.netloc, base+cur+"/"+path)
        if res == None:
            print "Request failed while testing %s" % cur
            return
        #print res.status,base+cur+"/"+path
        if default_data != "":
            if not difflib.get_close_matches(default_data,[res.read()]):
                success = True
                break
        elif default_code != res.status:
            success = True
            break
    if not success and not disable_dirmatch:
        res = do_request(target.netloc, base+cur+"/")
        if res == None:
            print "Request failed while testing %s" % cur
            return
        if default_data != "":
            if difflib.get_close_matches(default_data,[res.read()]):
                return
        elif default_code == res.status:
            return
    elif not success:        
        return
    #print "Plugin %s found. Doing version detection..." % cur

    #Found a plugin. Now we jump down our makeshift binary search tree
    #and find which version of the plugin is installed.
    s = sigs[cur][1]
    while 1:
        match = s[0].split(":")
        if match[-1] == "":
            break
        res = do_request(target.netloc, base+cur+"/"+match[0])
        data = res.read()
        if res == None:
            print "Request failed while doing version detection on  %s" % cur
            return
        if (default_code == res.status and default_data == "")\
           or (default_data != "" and difflib.get_close_matches(default_data,[data])):
            n = int(match[-1])^1 
        elif len(match) == 3 and hashlib.md5(data).hexdigest()!=match[1]:
            n = 1^int(match[2])
        else:
            n = int(match[-1])
        s = s[1+n]
        if type(s) != types.TupleType or s[0]=='':
            break
    if len(s) == 2:
        print "%s: %s" % (cur,s[1])
    elif s[0] != '':
        print "%s: %s" % (cur,s)
    else:
        print "%s: %s - %s" % (cur,s[1],s[2])

def finger_init(target):
    kw = {}
    res = do_request(target.netloc,target.path+"wp-content/plugins/"+
            "".join([random.choice(string.lowercase) for j in range(0,10)]))
    if res == None:
        print "Couldn't connect to server. Exiting..."
        sys.exit(0)
    
    default_code = res.status
    print "Detected %s as default response code." % default_code

    default_data = ""
    if default_code == 200:
        #Site is being tricky, let's see if we can match error page with difflib
        default_data = res.read()
        con = httplib.HTTPConnection(target.netloc)
        con.request("GET",target.path+"wp-content/plugins/"+
                "".join([random.choice(string.lowercase) for j in range(0,10)]))
        res = con.getresponse()
        if difflib.get_close_matches(default_data,[res.read()]):
            print "Was able to fingerprint tricky error page."
        else:
            print "Couldn't fingerprint error page. Results may be bad."
    return {
            'target':target,
            'default_code':default_code,
            'default_data':default_data,
            }
def scan_wordpress(target,pstats="plugin_stats.txt",limit=-1,threads=15,
        disable_dirmatch=False):
    '''
        Starts our scanning threads and waits for results.
    '''
    
    target = urlparse(target)
    
    kw = finger_init(target)
    kw['disable_dirmatch'] = disable_dirmatch
    plugins = [p.strip().split()[1] for p in open(pstats).readlines()]
    
    if limit == -1:
        limit = len(plugins)
    print "Installed plugins:" 
    gen = iter(plugins[0:limit])
    
    threads,out = get_threads(gen,finger,threads,**kw)

    for t in threads:
        t.join()
    return out


if __name__=="__main__":
    usage = "usage: %prog [options] [WORDPRESS_URL]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-g","--generate-sigs",action="store_true",
            help="Update repo, crawl stats, and generate signatures.")
    parser.add_option("-q","--quick-generate",action="store_true",
            help="Only perform signature generation (no stats/repo updates).")
    parser.add_option("-r","--repo",type=str,default="wordpress_plugins",
            help="Specify the path to the checked out repository.")
    parser.add_option("-p","--plugin",type=str,default="",
            help="Specify the plugin to scan/generate signature for.")
    parser.add_option("-n","--number",type=int,default=-1,
            help="Specify the number of plugins to scan/generate signatures for.")
    parser.add_option("-t","--threads",type=int,default=15,
            help="Specify the number of threads to scan with.")
    parser.add_option("-d","--disable-dirmatch",action="store_true",
            help="Disables the use of directories as last resort. Useful as a way\
 to speed things up, and possibly deal with difficult servers.")
    parser.add_option("-s","--signature-file",type=str,default="plugin_signatures.py",
            help="Specify the signature file to use (ex. sigs.py)")

    (opts,args) = parser.parse_args()
    if opts.generate_sigs or opts.quick_generate:
        if not opts.quick_generate:
            from grab_repos import checkout_plugins
            from get_download_counts import get_plugin_stats
            checkout_plugins(opts.repo)
            
            res = get_plugin_stats()
            res.sort(reverse=True)
            f = open("plugin_stats.txt","w")
            for p in res:
                f.write("%s %s\n" % p)
        if opts.plugin == "":
            sigs = fingerprint_plugins(base=opts.repo,limit=opts.number)
            open(opts.signature_file,"w").write(("sigs = " + repr(sigs)))
        else:
            generate_fingerprint(os.path.join(opts.repo,opts.plugin))
    if len(args) == 1:
        execfile(opts.signature_file)
        if opts.plugin == "":
            scan_wordpress(args[0],limit=opts.number,threads=opts.threads,
                    disable_dirmatch=opts.disable_dirmatch)
        else:
            kw = finger_init(urlparse(args[0]))
            kw['disable_dirmatch'] = opts.disable_dirmatch
            finger(opts.plugin,kw)
