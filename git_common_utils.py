#!/usr/bin/python
from __future__ import print_function
import sys
from subprocess import check_output, PIPE, STDOUT
import requests
import json
import datetime as dt
import os.path
import re

# Location of the Github Service account in GCP Storage Buckets
CREDENTIALS_BUCKET_NAME = "poc-infra-secrets"
USER_SECRET_NAME = "github_ro_user.secret"
TOKEN_SECRET_NAME = "github_ro_token.secret"
CREDENTIALS_URL = "gs://{0}/{1}"

# Default List of TEAM Reviewers to be configured for Pull Requests
DEFAULT_TEAM_REVIEWERS = ["reviewers"]
DEFAULT_USER_REVIEWERS = []
DEFAULT_PULL_REQUEST_TITLE = "Automatic Pull Request - Created on {0}"
DEFAULT_PULL_REQUEST_BODY = "Automatic Pull Request created on {0} by the Jenkins Job: {1}"

REPO_PREFIX = "" # Optional prefix to use to filter repos from all the repos in the organization
REPO_FILTER = "^{0}(?!excluded1|excluded2)".format(REPO_PREFIX)

GITHUB_ORG = "my-org"
GITHUB_REPOS_URL = "https://api.github.com/repos/{0}".format(GITHUB_ORG)
REPO_TOKENIZED_URL = "https://{0}:{1}@github.com/{2}/{3}.git"

DISTRIBUTION_LIST = "<DL-email>"


# Retrieves the Github Read-Only USER from the Credentials Bucket
def fetch_github_ro_user():
    return check_output( ["gsutil", "cat", CREDENTIALS_URL.format(CREDENTIALS_BUCKET_NAME, USER_SECRET_NAME)], stderr=STDOUT).rstrip()


# Retrieves the Github Read-Only TOKEN from the Credentials Bucket
def fetch_github_ro_token():
    return check_output( ["gsutil", "cat", CREDENTIALS_URL.format(CREDENTIALS_BUCKET_NAME, TOKEN_SECRET_NAME)], stderr=STDOUT).rstrip()


def get_authenticated_repository_url ( repositoryName, orgName = GITHUB_ORG ):

    github_user = fetch_github_ro_user()
    github_token = fetch_github_ro_token()
    githubURL=REPO_TOKENIZED_URL.format(github_user, github_token, orgName, repositoryName) # DO NOT PRINT IN STDOUT - It contains secrets
    return github_user, github_token, githubURL


# Retrieves all the branches in the remote
def get_branches(repositoryName, workingDir = "/tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None :
        raise Exception("[FATAL] Please provide a repository name")

    currentDir = switch_to_workspace(repositoryName, workingDir, cloneRepoIfNotPresent)

    branches = check_output( ["cd {0} && git fetch && git branch -r | grep -v HEAD".format(currentDir)], stderr=STDOUT, shell=True).rstrip().replace("origin/","").replace(" ","").split("\n")

    return branches


# Retrieves all the tags in the remote
def get_tags ( repositoryName, workingDir = "/tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None :
        raise Exception("[FATAL] Please provide a repository name")

    currentDir = switch_to_workspace(repositoryName, workingDir, cloneRepoIfNotPresent)

    tags = check_output( ["cd {0} && git tag".format(currentDir)], stderr=STDOUT, shell=True).rstrip().split("\n")

    return tags


#
# Clone a remote repository
#
def clone_repository ( repositoryName, workingDir = "/tmp"):

    if repositoryName is None :
        raise Exception("[FATAL] Please provide a repository name")

    repositoryPath = "{0}/{1}".format(workingDir, repositoryName)
    if os.path.isdir(repositoryPath):
        raise Exception("The directory {0}/{1} already exists. Cannot clone {1} at the location specified: {0}.".format(workingDir, repositoryName))

    githubUser, githubToken, githubURL = get_authenticated_repository_url ( repositoryName )

    output = check_output( ["cd {0} && git clone {1}".format(workingDir, githubURL)], stderr=STDOUT, shell=True).rstrip()

    return "{0}/{1}".format(workingDir, repositoryName)


#
# Switch to a workspace and make sure it is a Git repository
# Optionally Clone the requested repository if it is not present
#
# This is mnostly used as a utility step in other more complex tasks
#
# Returns the path of the repo
#
def switch_to_workspace ( repositoryName, workingDir = "/tmp", cloneRepoIfNotPresent = False, updateOrigin = True):

    errorPrefix = "[FATAL] Cannot switch to workspace: "

    if repositoryName is None :
        raise Exception("{0} Please provide a repository name".format(errorPrefix))

    if not os.path.isdir(workingDir):
        raise Exception("{0} The working directory: {1} does not exist or is not readable.".format(errorPrefix, workingDir))

    repositoryPath = "{0}/{1}".format(workingDir, repositoryName)
    if os.path.isdir(repositoryPath):
        if os.listdir(repositoryPath) == []:
            raise Exception("{0} {1} is an existing empty directory. Please remove it or chose another path.".format(errorPrefix, repositoryPath))
        else:
            output = check_output( ["cd {0} && git status . --porcelain".format(repositoryPath)], stderr=STDOUT, shell=True).rstrip()
            if re.search("^fatal: Not a git repository", output):  # There is a non-empty directory on that path but it is not a Git repo
                raise Exception("{0} {1} is not a git repository.".format(errorPrefix, repositoryPath))

            # If used by Jenkins, the origin might not have the credentials embedded,
            # causing the scripts to fail when performing operations on the remote
            if updateOrigin:
                # Get the Github Repository URL with authentication information embedded
                githubUser, githubToken, githubUrl = get_authenticated_repository_url( repositoryName )
                output = check_output( ["cd {0} && git remote set-url origin {1}".format(repositoryPath, githubUrl)], stderr=STDOUT, shell=True).rstrip()

                # Update the Global Git Config in case it is needed for rebase/commit
                output = check_output( ["cd {0} && git config --global --replace user.name {1} && git config --global --replace user.email {2}".format(repositoryPath, githubUser, DISTRIBUTION_LIST)], stderr=STDOUT, shell=True).rstrip()

            return repositoryPath
    else:
        if cloneRepoIfNotPresent is not True:   # The directory does not exist, therefore it is cloned and the function returns its path
            raise Exception("{0} {1} does not exist and cloneRepoIfNotPresent was False".format(errorPrefix, repositoryPath))
        else:
            return clone_repository(repositoryName, workingDir)


#
# Fetches the latest Tag for a given Github repository
#
def fetch_latest_tag_for_repo(repositoryName, tagFilter = "", workingDir = "/tmp", cloneRepoIfNotPresent = True):

    if repositoryName is None :
        raise Exception("[FATAL] Please provide a repository name")

    currentDir = switch_to_workspace(repositoryName, workingDir, cloneRepoIfNotPresent)

    latestTag = check_output( ["cd {0} && git for-each-ref --format=\"%(refname:short)\" --sort=-authordate --count=1 refs/tags/{1}".format(currentDir, tagFilter)], stderr=STDOUT, shell=True).rstrip()

    return latestTag


#
# Fetches the latest Tag for a given Github repository
#
def fetch_reference_tag_for_repo(repositoryName, tagEnv = "dev", workingDir = "/tmp", cloneRepoIfNotPresent = True):

    if repositoryName is None :
        raise Exception("[FATAL] Please provide a repository name")

    if tagEnv == "prod":
        tagFilter = "dta-pr-*"
    else:
        tagFilter = "dta-rc-*"

    currentDir = switch_to_workspace(repositoryName, workingDir, cloneRepoIfNotPresent)

    latestTag = fetch_latest_tag_for_repo(repositoryName, tagFilter, workingDir, cloneRepoIfNotPresent)

    referenceTag = check_output([
                        "cd {0} && git for-each-ref --format=\"%(refname:short)\" --sort=-authordate refs/tags/{1} --count=1 --no-contains={2}".format(
                            currentDir, tagFilter, latestTag)], stderr=STDOUT, shell=True).rstrip()

    return referenceTag


##############################################################################
#
# Creates a Branch on the given repository
# It it does exist, the script will try to check it out or raise and Exception
#
def create_branch_on_repo(repositoryName, branchName, workingDir = "/tmp", cloneRepoIfNotPresent = False, checkOutIfExisting = False):

    if repositoryName is None or branchName is None:
        raise Exception("[FATAL] Please provide branch and repository names")

    currentDir = switch_to_workspace(repositoryName, workingDir, cloneRepoIfNotPresent)

    # Check if the branch exists in the remote
    output = check_output( ["cd {0} &&  git ls-remote --heads origin {1}".format(currentDir, branchName)], stderr=STDOUT, shell=True).rstrip()

    # If the output does not contain the branch name, then it means it did not exist and can be created
    if re.search(branchName, output) is None:  # The branch does not exist in the remote

        # Create a branch if it does nto exist and switch to it
        output = check_output( ["cd {0} && git checkout -b {1}".format(currentDir, branchName)], stderr=STDOUT, shell=True ).rstrip()

    else:  # If the branch already exists in the remote, try to check it out locally
        if checkOutIfExisting:
            print ("[WARNING] Checking Out Existing Branch: '{0}' in repository: '{1}'.".format(branchName, repositoryName), file=sys.stderr)
            output = checkout_branch(repositoryName, branchName, workingDir, cloneRepoIfNotPresent)
        else:
            raise Exception ("[FATAL] Branch: '{0}' already exists in the repository: '{1}'.".format(branchName, repositoryName))


###########################
#
# Checks-out the given branch in the local workspace
#
def checkout_branch(repositoryName, branchName, workingDir = "/tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None or branchName is None:
        raise Exception("[FATAL] Please provide branch and repository names")

    currentDir = switch_to_workspace(repositoryName, workingDir, cloneRepoIfNotPresent)

    # Checkout the given branch. It will not error if the branch is already checked-out, only when the branch does not exist
    output = check_output( ["cd {0} && git checkout {1}".format(currentDir, branchName)], stderr=STDOUT, shell=True ).rstrip()
    if re.search("^error", output):  # The given branch does not exist
        raise Exception("[FATAL] Branch {1} could not be checked out in repository {0}.".format(errorPrefix, repositoryPath))


def rebase ( repositoryName, branchName, referenceBranch, remoteName = "origin", pushAfterRebase = True, workingDir = "tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None or branchName is None or referenceBranch is None:
        raise Exception("[FATAL] Please provide current branch, reference branch and repository names")

    # Try to rebase without conflicts. If conflicts are detected, the pipeline should stop here
    pull_changes_from_remote_branch ( repositoryName, referenceBranch, workingDir = workingDir, cloneRepoIfNotPresent = cloneRepoIfNotPresent )

    # If there has been a rebase, then the local branch will be out of sync with the remote one
    # The local branch needs to be rebased against the remote branch of the same name and then pushed
    pull_changes_from_remote_branch ( repositoryName, branchName, workingDir = workingDir, cloneRepoIfNotPresent = cloneRepoIfNotPresent )

    if pushAfterRebase:
        # Push any local updates to the remote branch
        push( repositoryName, branchName, workingDir  = workingDir)


def merge ( repositoryName, branchName, referenceBranch, remoteName = "origin", pushAfterMerge = True, workingDir = "tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None or branchName is None or referenceBranch is None:
        raise Exception("[FATAL] Please provide current branch, reference branch and repository names")

    # Try to rebase without conflicts. If conflicts are detected, the pipeline should stop here
    pull_changes_from_remote_branch ( repositoryName, referenceBranch, rebase = False, chooseRemoteOverLocal = False, workingDir = workingDir, cloneRepoIfNotPresent = cloneRepoIfNotPresent )

    # If there has been a rebase, then the local branch will be out of sync with the remote one
    # The local branch needs to be rebased against the remote branch of the same name and then pushed
    pull_changes_from_remote_branch ( repositoryName, branchName, rebase = False, chooseRemoteOverLocal = False, workingDir = workingDir, cloneRepoIfNotPresent = cloneRepoIfNotPresent )

    if pushAfterMerge:
        # Push any local updates to the remote branch
        push( repositoryName, branchName, workingDir  = workingDir)


#
# Pulls changes from a remote branch by Rebase or Merge
#
def pull_changes_from_remote_branch(repositoryName, remoteBranchName, remoteName = "origin", rebase = True, chooseRemoteOverLocal = False, workingDir = "/tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None or remoteBranchName is None:
        raise Exception("[FATAL] Please provide the remote branch name and repository name")


    currentDir = switch_to_workspace(repositoryName, workingDir, cloneRepoIfNotPresent)

    # Pull the latest changes from remote branch Changes from the master and merge giving precedence to changes in the remote branch over changes in the local branch
    pullCommand = ""
    if rebase:
        pullCommand = "cd {0} && git pull --rebase {2} {1}".format(currentDir, remoteBranchName, remoteName)
    elif chooseRemoteOverLocal is False :
        # Do not rebase but resign to edit the commit message
        pullCommand = "cd {0} && git pull --no-edit {2} {1}".format(currentDir, remoteBranchName, remoteName)
    else:
        # Use the recursive strategy with the 'theirs' option to prefer remote changes over local ones
        pullCommand = "cd {0} && git pull -s recursive --strategy-option theirs {2} {1}".format(currentDir, remoteBranchName, remoteName)


    output = check_output( [pullCommand], stderr=STDOUT, shell=True ).rstrip()
    print ("\n[DEBUG] Git Pull Command: {1}\n\nGit Pull Output {0}".format(output, pullCommand), file=sys.stderr)

    if re.search("([Ee][Rr][Rr][Oo][Oo][Rr]|[Ff][Aa][Ii][Ll][Ee][Dd]|[Cc][Aa][Nn][Nn][Oo][Tt])", output):
        raise Exception("[FATAL] Conflict found while pulling the changes from the remote branch {1}:{0} into current local branch.".format(remoteBranchName, remoteName))

    print ("\n[DEBUG] Changes successfully pulled from the remote branch {1}:{0} into current local branch".format(remoteBranchName, remoteName), file=sys.stderr)


#
# Pull changes from remote master into the local repository branch
#
def pull_changes_from_origin_master(repositoryName, rebase = True, chooseRemoteOverLocal = False, workingDir = "/tmp", cloneRepoIfNotPresent = False):
    return pull_changes_from_remote_branch(repositoryName, "master", rebase = rebase, chooseRemoteOverLocal = chooseRemoteOverLocal, workingDir = workingDir, cloneRepoIfNotPresent = cloneRepoIfNotPresent)


#
# Switches to the repository local workspace or raises an exception if it can't
# Checks for any changes to be committed or raises and exception if there are none
# Finally adds, commits any changes
#
def add_commit(repositoryName, commitMessage, workingDir = "/tmp"):

    if repositoryName is None or commitMessage is None:
        raise Exception("[FATAL] Please provide a commit message and a repository name")

    # Switch to the requested workspace, or raise an exception if it is not possible
    currentDir = switch_to_workspace(repositoryName, workingDir)

    # Check if there are local changes, or raise an exception otherwise
    output = check_output( ["cd {0} && git status . --porcelain".format(currentDir)], stderr=STDOUT, shell=True).rstrip()
    if re.match("^\s*$", output):  # No changes to add or commit
        raise Exception("[FATAL] There are no changes to add or commit on the repository at {0}.".format(currentDir))

    # Add any new files and changed files to source control
    output = check_output( ["cd {0} && git add .".format(currentDir)], stderr=STDOUT, shell=True ).rstrip()

    # Add changes to source control and commit the changes
    output = check_output( ["cd {0} && git commit -am '{1}'".format(currentDir, commitMessage)], stderr=STDOUT, shell=True ).rstrip()


#
# Switches to the repository local workspace or raises an exception if it can't
# Checks for any changes to be committed and pushed, or raises and exception if there are none
# Finally adds, commits and pushes any changes
#
def add_commit_and_push(repositoryName, commitMessage, localBranch, remoteName = "origin", remoteBranch = None, workingDir = "/tmp", force = False):

    if repositoryName is None or localBranch is None or commitMessage is None:
        raise Exception("[FATAL] Please provide a commit message, a branch and a repository name")

    # Default behaviour is to push to a remote branch named as the local branch
    if remoteBranch is None:
        remoteBranch = localBranch

    # Switch to the requested workspace, or raise an exception if it is not possible
    currentDir = switch_to_workspace(repositoryName, workingDir)

    # Check if there are local changes, or raise an exception otherwise
    output = check_output( ["cd {0} && git status . --porcelain".format(currentDir)], stderr=STDOUT, shell=True).rstrip()
    if re.match("^\s*$", output):  # No changes to add or commit
        raise Exception("[FATAL] There are no changes to add or commit on the repository at {0}.".format(currentDir))

    # Add any new files and changed files to source control
    output = check_output( ["cd {0} && git add .".format(currentDir)], stderr=STDOUT, shell=True ).rstrip()

    # Add changes to source control and commit the changes
    output = check_output( ["cd {0} && git commit -am '{1}'".format(currentDir, commitMessage)], stderr=STDOUT, shell=True ).rstrip()

    # Push the changes to the remote
    if force:
        output = check_output( ["cd {0} && git push {3} {1}:{2} --force".format(currentDir, localBranch, remoteBranch, remoteName)], stderr=STDOUT, shell=True ).rstrip()
    else:
        output = check_output( ["cd {0} && git push {3} {1}:{2}".format(currentDir, localBranch, remoteBranch, remoteName)], stderr=STDOUT, shell=True ).rstrip()


#
# Switches to the repository local workspace or raises an exception if it can't
# Pushes the changes to the requested remote branch, forcing th epush if required
#
def push(repositoryName, localBranch, remoteName = "origin", remoteBranch = None, workingDir = "/tmp", force = False):

    if repositoryName is None or localBranch is None:
        raise Exception("[FATAL] Please provide a local branch and a repository name. Optionally include a remote name and remote branch name.")

    # Default behaviour is to push to a remote branch named as the local branch
    if remoteBranch is None:
        remoteBranch = localBranch

    # Switch to the requested workspace, or raise an exception if it is not possible
    currentDir = switch_to_workspace(repositoryName, workingDir)

    # Push the changes to the remote
    if force:
        output = check_output( ["cd {0} && git push {3} {1}:{2} --force".format(currentDir, localBranch, remoteBranch, remoteName)], stderr=STDOUT, shell=True ).rstrip()
    else:
        output = check_output( ["cd {0} && git push {3} {1}:{2}".format(currentDir, localBranch, remoteBranch, remoteName)], stderr=STDOUT, shell=True ).rstrip()


# Adds a remote definition to the local git repository
def add_remote (repositoryName, remoteName, remoteURL, workingDir = "/tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None or remoteName is None or remoteURL is None :
        raise Exception("[FATAL] Please provide a repository name, remote name and remote URL")

    currentDir = switch_to_workspace ( repositoryName, workingDir, cloneRepoIfNotPresent)

    # Create the remote
    output = check_output( ["cd {0} && git remote add {1} {2}".format(currentDir, remoteName, remoteURL)], stderr=STDOUT, shell=True).rstrip()


# Fetch changes from a remote
def fetch (repositoryName, remoteName = "--all", prune = "--prune", tags= "--no-tags", workingDir = "/tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None or remoteName is None:
        raise Exception("[FATAL] Please provide a repository name and a remote name (or --all)")

    currentDir = switch_to_workspace ( repositoryName, workingDir, cloneRepoIfNotPresent)

    # Fetch the changes from the requested remotes
    output = check_output( ["cd {0} && git fetch {1} {2} {3}".format(currentDir, remoteName, prune, tags)], stderr=STDOUT, shell=True).rstrip()

    print ("\n[DEBUG] Fetch Results: {0}".format(output), file=sys.stderr)

    return currentDir


# Call fetch with the defaults --all --prune --no-tags
def fetch_all (repositoryName, workingDir = "/tmp", cloneRepoIfNotPresent = False):
    return fetch (repositoryName, workingDir = workingDir, cloneRepoIfNotPresent = cloneRepoIfNotPresent)


# Fetch changes from a remote
def track_branch (repositoryName, remoteName, branchName, workingDir = "/tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None or remoteName is None or branchName is None:
        raise Exception("[FATAL] Please provide a repository name, remote name, and branch name")

    currentDir = switch_to_workspace ( repositoryName, workingDir, cloneRepoIfNotPresent)

    # First check if the branch already exists locally
    output = check_output( ["cd {0} && git branch".format(currentDir)], stderr=STDOUT, shell=True).rstrip()

    if not re.search( "(?:^{0}$)|(?:\\s+{0}$)".format(branchName), output):
        # Create a local branch to track a remote branch
        output = check_output( ["cd {0} && git branch --track {2} {1}/{2}".format(currentDir, remoteName, branchName)], stderr=STDOUT, shell=True).rstrip()

    print ("\n[DEBUG] Track Branch result: {0}".format(output), file=sys.stderr)

    return currentDir


#
# Diff the current branch against a reference branch and find the modified paths
# This function is customized to be used with the monorepo and it will try to find project or role paths
#
def diffWithReferenceBranch ( repositoryName, referenceBranch = 'integration', workingDir = "/tmp", cloneRepoIfNotPresent = False, startsWith = "", groupPathsByEndingRegex = "" ):

    if repositoryName is None:
        raise Exception("[FATAL] Please provide a repository name")

    # Update the origin remote to make sure the reference branch is known to git
    currentDir = track_branch ( repositoryName, remoteName = "origin", branchName = referenceBranch, workingDir = workingDir, cloneRepoIfNotPresent = cloneRepoIfNotPresent)

    # Highlight files that have been renamed but are 100% identical to their original
    # Those files won't be considered as changes from the reference branch
    diffCommand = "cd {0} && git diff --name-status {1} | egrep -v \"^R100\" | awk '{{print $NF}}'".format(currentDir, referenceBranch)

    if (startsWith != ""):
        diffCommand += " | grep -e '^{0}/'".format(startsWith)

    # Group changes by trailing pattern so all files in a sub-tree are grouped as one changed folder in the results
    if (groupPathsByEndingRegex != ""):
        diffCommand += " | sed -nr 's/({0}).*/\\1/p'".format(groupPathsByEndingRegex)

    diffCommand += " | uniq"

    print ("\n[DEBUG] Diff Command: {0}".format(diffCommand), file=sys.stderr)

    changedPaths = check_output( diffCommand, stderr=STDOUT, shell=True).rstrip().split('\n')

    return changedPaths


#
# Diff the current branch against a reference branch and find the modified paths
# This function is customized to be used with the monorepo and it will try to find project or role paths
#
def diffWithReferenceTag ( repositoryName, referenceTag, currentTag, workingDir = "/tmp", cloneRepoIfNotPresent = False, startsWith = "", groupPathsByEndingRegex = "" ):

    if repositoryName is None:
        raise Exception("[FATAL] Please provide a repository name")

    if referenceTag is None:
        raise Exception("[FATAL] Please provide a reference release name")

    if currentTag is None:
        raise Exception("[FATAL] Please provide a the current release")

    currentDir = switch_to_workspace(repositoryName, workingDir, cloneRepoIfNotPresent)

    # Get all branches and tags so we can compare tags locally
    output = check_output(["cd {0} && git fetch".format(currentDir)], stderr=STDOUT, shell=True).rstrip()

    # Highlight files that have been renamed but are 100% identical to their original
    # Those files won't be considered as changes from the reference branch
    # Also removes projects which only has deleted files
    diffCommand = "cd {0} && git diff --name-status {1} {2} | egrep -v \"^R100\" | egrep -v \"^D\" | awk '{{print $NF}}'".format(currentDir, referenceTag, currentTag)

    if (startsWith != ""):
        diffCommand += " | grep -e '^{0}/'".format(startsWith)

    # Group changes by trailing pattern so all files in a sub-tree are grouped as one changed folder in the results
    if (groupPathsByEndingRegex != ""):
        diffCommand += " | sed -nr 's/({0}).*/\\1/p'".format(groupPathsByEndingRegex)

    diffCommand += " | uniq"

    print ("\n[DEBUG] Diff Command: {0}".format(diffCommand), file=sys.stderr)

    changedPaths = check_output( diffCommand, stderr=STDOUT, shell=True).rstrip().split('\n')

    return changedPaths


# Merges a remote branch into a local branch
def merge_into_subtree (repositoryName, remoteName, subtree, localBranch, remoteBranch = "master", workingDir = "/tmp", cloneRepoIfNotPresent = False):

    if repositoryName is None or remoteName is None or subtree is None or localBranch is None or remoteBranch is None:
        raise Exception("[FATAL] Please provide a repository name, local branch name, remote name, subtree and commit message")

    # Make sure are in the required localBranch
    checkout_branch(repositoryName, localBranch, workingDir, cloneRepoIfNotPresent)

    # Switch to the requested workspace, or raise an exception if it is not possible
    currentDir = switch_to_workspace(repositoryName, workingDir)
    monorepoSubtree = "{0}/{1}".format(currentDir, subtree)
    command = ""

    if os.path.isdir(monorepoSubtree):
        command = "pull"
    else:
        command = "add"

    output = check_output( ["cd {0} && git subtree {4} -P {1} {2} {3} -m \"Merging {2}/{3} into {1}\"".format(currentDir, subtree, remoteName, remoteBranch, command)], stderr=STDOUT, shell=True ).rstrip()

    return output

#############################################
#
#   GITHUB API UTILITY FUNCTIONS
#
############################################


#
# Lists all private repositories the github_ro_user has access to but filtered by its affiliation (Collaborator, organization_member, Owner)
# https://developer.github.com/v4/enum/repositoryaffiliation/
#
def list_all_repos (visibility = "private", affiliation = "collaborator", per_page = "100"):

    github_user = fetch_github_ro_user()
    github_token = fetch_github_ro_token()
    url = "https://api.github.com/user/repos?visibility="+visibility+"&affiliation="+affiliation+"&per_page="+per_page
    result = []

    more_pages = True
    while more_pages :

        response = requests.get( url, headers={"Content-Type": "application/json"}, auth=(github_user, github_token))
        try:
            response.raise_for_status()  # Raises an Exception if the response.status_code is 4xx or 5xx
        except Exception as e:
            print ("\n[FATAL] "+response.text+"\n", file=sys.stderr)
            raise e

        more_pages = False
        if "next" in response.links and "url" in response.links["next"] and response.links["next"]["url"] != "":
            more_pages = True
            url = response.links["next"]["url"]
            #print ("[DEBUG] MorePages: {0} Next: {1}".format(more_pages, response.links["next"]["url"]), file=sys.stderr)

        reposInPage = response.json()
        for r in reposInPage:
            result.append(r["name"])

        #print ("[DEBUG] Result Size: {0}".format(len(result)), file=sys.stderr)

    return result


#
# Lists all private repositories the github_ro_user has access to but filtered by its affiliation (Collaborator, organization_member, Owner)
# https://developer.github.com/v4/enum/repositoryaffiliation/
#
def list_repos_with_filter (visibility = "private", affiliation = "collaborator", filterRegex = REPO_FILTER):

    result = []
    unfilteredList = list_all_repos (visibility, affiliation)

    for repoName in unfilteredList:
        if re.search(filterRegex, repoName):
            result.append(repoName)

    print ("[DEBUG] Num Filtered Repos: {0}".format(len(result)), file=sys.stderr)

    return result


#
# Lists all private repositories the github_ro_user has access to, but filtered by its affiliation (Collaborator , organization_member, Owner)
# https://developer.github.com/v4/enum/repositoryaffiliation/
#
# NOTE: Default repository permission
# The organization has their default repository permission set to read.
# This means that every member of this organization has read access to this repository,
# regardless of the team and collaborator access specified below.
# To change or remove this organization's default repository permission, contact one of the organization's owners.
#
def list_all_filtered_repos (visibility = "private", affiliation = "collaborator"):

    return list_repos_with_filter (visibility, affiliation, filterRegex = REPO_FILTER)


#
# https://developer.github.com/v3/repos/collaborators/#review-a-users-permission-level
# Possible values for the permission key: admin, write, read, none.
#
def get_user_permission_on_repo (repositoryName, userAccount = ""):

    github_user = fetch_github_ro_user()
    github_token = fetch_github_ro_token()

    if userAccount == "":
        userAccount = github_user

    # GET /repos/:owner/:repo/collaborators/:username/permission
    url = "{2}/{0}/collaborators/{1}/permission".format(repositoryName, userAccount, GITHUB_REPOS_URL)

    response = requests.get(url, headers={"Content-Type": "application/json"}, auth=(github_user, github_token))
    try:
        response.raise_for_status() # Raises an Exception if the response.status_code is 4xx or 5xx
    except Exception as e:
        print ("\n[FATAL] {0}\n".format(response.text), file=sys.stderr)
        raise e

    permission = response.json()['permission']

    return permission


#
#
#
def check_user_is_a_collaborator (repositoryName, userAccount = ""):

    github_user = fetch_github_ro_user()
    github_token = fetch_github_ro_token()

    if userAccount == "":
        userAccount = github_user

    # GET /repos/:owner/:repo/collaborators/:username
    url = "{2}/{0}/collaborators/{1}".format(repositoryName, userAccount, GITHUB_REPOS_URL)

    response = requests.get(url, headers={"Content-Type": "application/json"}, auth=(github_user, github_token))
    try:
        response.raise_for_status() # Raises an Exception if the response.status_code is 4xx or 5xx
    except Exception as e:
        if response.status_code >= 500:
            print ("\n[FATAL] {0}\n".format(response.text), file=sys.stderr)
            raise e

    return (response.status_code == 204)


# UNTESTED
# Adds a user as a collaborator on th e repo with the specified permission
# https://developer.github.com/v3/repos/collaborators/#add-user-as-a-collaborator
# Possible values for the permission key: admin, write, read, none.
#
def add_collaborator (repositoryName, userAccount = "", permission = "read"):

    github_user = fetch_github_ro_user()
    github_token = fetch_github_ro_token()

    if userAccount == "":
        userAccount = github_user

    url = "{3}/{0}/collaborators/{1}?permission={2}".format(repositoryName, userAccount, permission, GITHUB_REPOS_URL)
    data = json.loads('''{ "permission": "'''+permission+'''" }''')
    response = requests.put(url, headers={"Content-Type": "application/json"}, auth=(github_user, github_token), json=data)
    try:
        response.raise_for_status() # Raises an Exception if the response.status_code is 4xx or 5xx
    except Exception as e:
        print ("\n[FATAL] {0}\n".format(response.text), file=sys.stderr)
        raise e

    if response.status_code == 204:
        print ("\n[DEBUG] User {0} was already a collaborator on the repository {1}".format(userAccount, repositoryName), file=sys.stderr)
    elif response.status_code == 201:
        print ("\n[DEBUG] User {0} has been added as a collaborator on the repository {1}".format(userAccount, repositoryName), file=sys.stderr)


############################################################################################
#
# Creates a Pull Request on the branchName of the repositoryName
# By default it will use a default Title, Body and list of team_reviewers defined above
# but it is possible to override those defaults when the function is called
#
def create_pull_request(repositoryName,
                        branchName,
                        baseBranch = "master",
                        title = DEFAULT_PULL_REQUEST_TITLE.format(dt.datetime.now().strftime('%Y%m%d%H%M%S')),
                        body = DEFAULT_PULL_REQUEST_BODY.format(dt.datetime.now().strftime('%Y%m%d%H%M%S'), DEFAULT_JENKINS_JOB_URL) ):

  github_user = fetch_github_ro_user()
  github_token = fetch_github_ro_token()

  #print ("\n[DEBUG] PR Body: {0}".format(body), file=sys.stderr)

  url = "{0}/{1}/pulls".format(GITHUB_REPOS_URL, repositoryName)
  dataToLoad = "{{ \"title\": \"{0}\", \"body\": \"{1}\", \"head\": \"{2}\", \"base\": \"{3}\" }}".format(title, body, branchName, baseBranch)

  #print ("\n[DEBUG] Data to Load: {0}".format(dataToLoad), file=sys.stderr)

  data = json.loads(dataToLoad)

  #print ("\n[DEBUG] PR DATA: "+json.dumps(data), file=sys.stderr)

  response = requests.post(url, headers={"Content-Type": "application/json"}, auth=(github_user, github_token), json=data)
  try:
      response.raise_for_status() # Raises an Exception if the response.status_code is 4xx or 5xx
  except Exception as e:
      if re.search("No commits between", response.text):
          print ("[WARNING] No Commits found between the base branch '{0}' and the '{1}' branch".format(baseBranch, branchName), file=sys.stdout)
          return True  # Nothing else to do
      else:
          print ("\n[FATAL] {0}\n".format(response.text), file=sys.stderr)
          raise e

  pullRequestNumber = json.loads(response.text)['number']
  print ("\n[INFO] Pull Request #"+json.dumps(pullRequestNumber)+" has been created successfully\n", file=sys.stdout)

  return pullRequestNumber




############################################################################################
#
# Creates a Pull Request on the branchName of the repositoryName
# By default it will use a default Title, Body and list of team_reviewers defined above
# but it is possible to override those defaults when the function is called
#
def request_reviewers (repositoryName,
                        pullRequestNumber,
                        reviewers = DEFAULT_USER_REVIEWERS,
                        team_reviewers = DEFAULT_TEAM_REVIEWERS ):

  github_user = fetch_github_ro_user()
  github_token = fetch_github_ro_token()

  # Create the Review Requests
  # If you need to assign a list of individual users, the API parameter is called reviewers instead of team_reviewers
  # https://developer.github.com/v3/pulls/review_requests/
  url = "{2}/{0}/pulls/{1}/requested_reviewers".format(repositoryName, pullRequestNumber, GITHUB_REPOS_URL)
  json_reviewers='''{ "team_reviewers": '''+json.dumps(team_reviewers)+''', "reviewers": '''+json.dumps(reviewers)+''' }'''
  data = json.loads(json_reviewers)

  response = requests.post(url, headers={"Content-Type": "application/json"}, auth=(github_user, github_token), json=data)
  try:
      response.raise_for_status() # Raises an Exception if the response.status_code is 4xx or 5xx
  except Exception as e:
      print ("\n[FATAL] "+response.text+"\n", file=sys.stderr)
      raise e

  print ("\n[INFO] Review requests have been raised successfully for Pull Request #"+json.dumps(pullRequestNumber), file=sys.stdout)
  print ("\n[INFO] Team Reviewers: {0}\n[INFO] User Reviewers: {1}\n".format(team_reviewers, reviewers), file=sys.stdout)
