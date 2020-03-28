#!/usr/bin/python
import re

import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import git_common_utils as utils

#def create_branch_on_repo(repositoryName, branchName, workingDir = "/tmp", cloneRepoIfNotPresent = False):
def usage():
  print "[INFO] Usage: {0} <repositoryName> <branchName> [(true|false)] [<working path>]".format(sys.argv[0])
  sys.exit(1)

if len(sys.argv)<3 :
    usage()


REPO_NAME = sys.argv[1]
BRANCH_NAME = sys.argv[2]
CLONE_REPO=False

if len(sys.argv)>3 :

    if re.match("[Tt][Rr][Uu][Ee]", sys.argv[3]) :
        CLONE_REPO=True

    if len(sys.argv)>4 :
        WORKING_DIR = sys.argv[4]
        utils.create_branch_on_repo(REPO_NAME, BRANCH_NAME, cloneRepoIfNotPresent=CLONE_REPO, workingDir=WORKING_DIR)
    else:
        utils.create_branch_on_repo(REPO_NAME, BRANCH_NAME, cloneRepoIfNotPresent=CLONE_REPO)

else:
    latestTag = utils.create_branch_on_repo(REPO_NAME, BRANCH_NAME)

print "[INFO] Branch '{0}' was created successfully on the repository '{1}'".format(BRANCH_NAME, REPO_NAME)
