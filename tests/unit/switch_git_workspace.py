#!/usr/bin/python
import re, os, sys, inspect

# This is needed to find the git_common_utils module since this Unit test is not within the same module
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
grandparentdir = os.path.dirname(parentdir)
sys.path.insert(0,grandparentdir)
import git_common_utils

#switch_to_workspace(repositoryName, workingDir = "/tmp", cloneRepoIfNotPresent = False):
def usage():
  print "[INFO] Usage: {0} <repositoryName> [(true|false)] [<working path>]".format(sys.argv[0])
  sys.exit(1)

if len(sys.argv)<2 :
    usage()

CLONE_REPO=False
repositoryPath=""
REPO_NAME = sys.argv[1]
if len(sys.argv)>2 :

    if re.match("[Tt][Rr][Uu][Ee]", sys.argv[2]) :
        CLONE_REPO=True

    if len(sys.argv)>3 :
        WORKING_DIR = sys.argv[3]
        repositoryPath = git_common_utils.switch_to_workspace(REPO_NAME, cloneRepoIfNotPresent=CLONE_REPO, workingDir=WORKING_DIR)
    else:
        repositoryPath = git_common_utils.switch_to_workspace(REPO_NAME, cloneRepoIfNotPresent=CLONE_REPO)

else:
    repositoryPath = git_common_utils.switch_to_workspace(REPO_NAME) # Default is used for Working Dir

print "[INFO] Switched to the repository at {0} - CloneIfNotPresent={1}".format(repositoryPath, CLONE_REPO)
