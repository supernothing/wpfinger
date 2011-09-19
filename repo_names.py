import urllib2
import sys
import time

def do_request(url,retries=5):
    i = 0
    while i < retries:
        try:
            return  urllib2.urlopen(url)
        except:
            i+=1
            time.sleep(5)
            continue
    return None

def get_names(url):
    data = urllib2.urlopen(url).read()
    data = data.split('href="')[1:]
    return [i.split('/">')[0] for i in data[:len(data)-1]]

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: %s SVN_ROOT OUTFILE"
        sys.exit(0)
    open(sys.argv[2],"w").write("data = %s" % repr(get_names(sys.argv[1])))
