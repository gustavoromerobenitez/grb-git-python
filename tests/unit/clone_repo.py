#!/usr/bin/python
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
grandparentdir = os.path.dirname(parentdir)
sys.path.insert(0,grandparentdir)

import git_common_utils

def usage():
  print "[INFO] Usage: {0} <repositoryName> [<working path>]".format(sys.argv[0])
  sys.exit(1)

if len(sys.argv)<2 :
    usage()

repositoryPath=""
REPO_NAME = sys.argv[1]
if len(sys.argv)>2 :
    WORKING_DIR = sys.argv[2]
    repositoryPath = git_common_utils.clone_repository(REPO_NAME, WORKING_DIR)
else:
    repositoryPath = git_common_utils.clone_repository(REPO_NAME) # Default is used for Working Dir

print "[INFO] Repository cloned at {0}".format(repositoryPath)
