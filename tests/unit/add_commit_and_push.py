#!/usr/bin/python
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
grandparentdir = os.path.dirname(parentdir)
sys.path.insert(0,grandparentdir)

import git_common_utils

#add_commit_and_push(repositoryName, branchName, commitMessage, workingDir = "/tmp")
def usage():
  print "[INFO] Usage: {0} <repositoryName> <branchName> <commitMessage> [<working path>]".format(sys.argv[0])
  sys.exit(1)

if len(sys.argv)<4 :
    usage()

REPO_NAME = sys.argv[1]
BRANCH_NAME = sys.argv[2]
COMMIT_MESSAGE = sys.argv[3]

if len(sys.argv)>4 :
    WORKING_DIR = sys.argv[4]
    git_common_utils.add_commit_and_push(REPO_NAME, BRANCH_NAME, COMMIT_MESSAGE, workingDir=WORKING_DIR)
else:
    git_common_utils.add_commit_and_push(REPO_NAME, BRANCH_NAME, COMMIT_MESSAGE)

print "[INFO] Changes Added, Commited to the Branch '{0}' with message '{1}' and pushed to the remote on repo '{2}'".format(BRANCH_NAME, COMMIT_MESSAGE, REPO_NAME)
