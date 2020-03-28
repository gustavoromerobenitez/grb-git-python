#!/usr/bin/python
import os,sys,inspect
import re
import datetime as dt
import argparse


currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import git_common_utils as utils

from subprocess import check_output, PIPE, STDOUT


def usage():
  print '''\n[INFO] Usage: {0} [--repos=<repositoryName1>,..,<repositoryNameN>]
[INFO] - The script will scan all filterd repositories where the GITHUB service account is a collaborator.
[INFO] - However, if a list of repository names is provided with the "--repos" argument, then the script will only check the given repositories.
[INFO] - For each repository it will check which permissions Github has on the repository.'''.format(sys.argv[0])
  sys.exit(1)



############################################################
#
#   MAIN
#
############################################################

# [START run]
def main(repositoriesArgumentList):

    # RunAs User Check
    runAsUser = check_output( ["id -un"], stderr=STDOUT, shell=True).rstrip()
    if runAsUser != "tf":
        raise Exception("\n\n[FATAL] This script must be run as the tf user.\n\n")

    if "all" in repositoriesArgumentList:
        repoList = utils.list_all_filtered_repos(affiliation = "organization_member")
    else:
        repoList = repositoriesArgumentList

    print "[DEBUG] FILTERED REPO LIST: {0}".format(repoList)

    userAccount = utils.fetch_github_ro_user()
    incorrectRepos = []
    for repoName in repoList:

        isCollaborator = utils.check_user_is_a_collaborator(repoName)
        if isCollaborator:
            permission = utils.get_user_permission_on_repo(repoName)
            print "[INFO] User {0} is a collaborator on the repository {1} with permission {2}".format(userAccount, repoName, permission)
        else:
            print "[INFO] User {0} is NOT a collaborator on the repository {1}".format(userAccount, repoName)
            incorrectRepos.append(repoName)

        #if (not isCollaborator or permission != "admin"):
        #    utils.add_collaborator(repoName, userAccount = "", permission = "owner")

    print "\n[INFO] INCORRECT REPOS: {0}".format(incorrectRepos)


if __name__ == '__main__':
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r','--repositories', required=True, metavar='repositories', nargs='+', help='List of one or more Github repositories to perform the actions on.\nUse -r all to scan all filtered repositories.')
    args = parser.parse_args()
    main(args.repositories)
# [END run]
