#!/usr/bin/python
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
grandparentdir = os.path.dirname(parentdir)
sys.path.insert(0,grandparentdir)

import git_common_utils

def usage():
  # https://developer.github.com/v3/repos/#list-your-repositories
  # Parameters allowed: Visibility, Affiliation
  print "[INFO] Usage: {0} [(all|public|private)] [(owner|collaborator|organisation_member)]".format(sys.argv[0])
  sys.exit(1)


if len(sys.argv)>1 :
    VISIBILITY = sys.argv[1]
    if len(sys.argv)>2 :
        AFFILIATION = sys.argv[2]
        repoList = git_common_utils.list_all_repos (VISIBILITY, AFFILIATION)
    else:
        repoList = git_common_utils.list_all_repos (VISIBILITY)
else:
    repoList = git_common_utils.list_all_repos () # Defaults are used

for r in repoList:
    print "[INFO] - "+ r
