#!/usr/bin/env python

import sys
import os
from subprocess import Popen, PIPE
from optparse import OptionParser


def get_result(p):
    stdout = p.communicate()
    ret = 1
    for s in stdout:
        if s != None:
            l = s.strip("\n".encode())
            if l == "0":
                ret = 0
            break
        
    return ret

def run_cmd(cmd):
    p = Popen(cmd, shell = True, stdout = PIPE)
    p.wait()
    
    return get_result(p)

def find_files(dir_path, libname):
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            file_path = "%s/%s" % (root, f)
            cmd = 'ldd '+file_path + '| grep libmpi'
            print(cmd)
            if run_cmd(cmd) == 0:
                cmd = "ldd %s | grep %s 2>&1 > /dev/null ; echo $?" % (file_path, libname)
                if run_cmd(cmd) == 0:
                    print("file [%s] is used %s" % (file_path, libname))
                

def start_find_files(directories, libname):
    for d in directories:
        find_files(d, libname)

def get_directories(directory):
    ret = []
    tmp = directory.split(",")

    for d in tmp:
        ret.append(d)

    return ret

def get_options():
    parser = OptionParser()
    parser.add_option("-d", "--directory", dest="directories", 
                      help="Directories which are divided by camma", metavar="DIRECTORY")
    parser.add_option("-l", "--library", dest="library",
                      help="library name", metavar="LIBRARY")

    (options, args) = parser.parse_args()
    return options

if __name__ == "__main__":
    options = get_options()

    
    directory = options.directories
 
    directories = get_directories(directory)
    
    libname = options.library
 

    start_find_files(directories, libname)
