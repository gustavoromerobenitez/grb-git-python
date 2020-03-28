#!/usr/bin/python
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
grandparentdir = os.path.dirname(parentdir)
sys.path.insert(0,grandparentdir)

import git_common_utils as utils

from subprocess import check_output, PIPE, STDOUT


############################################################
#
#   MAIN
#
############################################################

# RunAs User Check
runAsUser = check_output( ["id -un"], stderr=STDOUT, shell=True).rstrip()
if runAsUser != "tf":
    print "\n\n[FATAL] This script must be run as the tf user.\n\n"
    sys.exit(1)

# Read the Repository List or retrieve all filtered repos
repoList = utils.list_all_filtered_repos(affiliation = "organization_member")

if len(repoList) == 0:
    print "\n\n[ERROR] No repositories could be retrieved.\n\n"
    sys.exit(2)

print "\n\n[INFO] {0} repositories retrieved from Github:".format(len(repoList))
for repo in repoList:
    print "{0}".format(repo)

sys.exit(0)
