#!/usr/bin/python
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import git_common_utils as utils



def usage():
  print ('[INFO] Usage: '+sys.argv[0]+' <repositoryName> <branch> [optionalUserReviewer-1..optionalUserReviewer-N]')
  sys.exit(1)

if len(sys.argv)<3:
  usage()

REPO_NAME = sys.argv[1]
FEATURE_BRANCH = sys.argv[2]

# Check if an overriding list of User reviewers has been specified as a script argument

# The function provides defaults for PR Title, PR Body and List of Team Reviewers
pullRequestNumber = utils.create_pull_request(REPO_NAME, FEATURE_BRANCH)

REVIEWERS = []
if len(sys.argv)>3 :
    REVIEWERS = sys.argv[3:len(sys.argv)]

utils.request_reviewers(REPO_NAME, pullRequestNumber, reviewers=REVIEWERS)
