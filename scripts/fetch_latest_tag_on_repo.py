#!/usr/bin/python
import re

import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import git_common_utils as utils

#def fetch_latest_tag_for_repo(repositoryName, workingDir = "/tmp", cloneRepoIfNotPresent = True):
def usage():
  print "[INFO] Usage: {0} <repositoryName> [(true|false)] [<working path>]".format(sys.argv[0])
  sys.exit(1)

if len(sys.argv)<2 :
    usage()

# It is likely that the repository won't exist locally so we default to cloning it as the original function does
CLONE_REPO=True
latestTag=""
REPO_NAME = sys.argv[1]
if len(sys.argv)>2 :

    if re.match("[Ff][Aa][Ll][Ss][Ee]", sys.argv[2]) :
        CLONE_REPO=False

    if len(sys.argv)>3 :
        WORKING_DIR = sys.argv[3]
        latestTag = utils.fetch_latest_tag_for_repo(REPO_NAME, cloneRepoIfNotPresent=CLONE_REPO, workingDir=WORKING_DIR)
    else:
        latestTag = utils.fetch_latest_tag_for_repo(REPO_NAME, cloneRepoIfNotPresent=CLONE_REPO)

else:
    latestTag = utils.fetch_latest_tag_for_repo(REPO_NAME) # Default is used for Working Dir

print "[INFO] Latest Tag on the {0} repository is {1}".format(REPO_NAME, latestTag)
