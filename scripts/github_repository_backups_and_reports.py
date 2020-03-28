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

# globalVars
globalVars = {}
globalVars["BASE_WORKSPACE"] = "/projects/github_repo_backups"
globalVars["VERSION_REPORT"] = []
globalVars["VERSION_REPORT_BASE_FILENAME"] = "repositories-version-report"
globalVars["VERSION_REPORT_FILE_EXTENSION"] = "csv"
globalVars["RETENTION_DAYS"] = "14"


def writeReport(date):
    versionReportFilename = "{0}_{1}.{2}".format(globalVars["VERSION_REPORT_BASE_FILENAME"], date, globalVars["VERSION_REPORT_FILE_EXTENSION"])
    print "\n\n[INFO] Writing Version Report to file {0}".format(versionReportFilename)

    with open(versionReportFilename, 'w') as f:
        for line in globalVars["VERSION_REPORT"]:
            f.write("{0}\n".format(line))



def report_version(repoName, fileName, regularExpression):
    file = open(fileName, 'r')
    fileContents = file.read()
    file.close()
    for match in re.finditer(regularExpression, fileContents):
        itemName = match.group(1)
        itemVersion = match.group(2)
        versionString = "{0}\t{1}\t{2}\t{3}".format(repoName, itemName, itemVersion, fileName)
        globalVars["VERSION_REPORT"].append(versionString)
        print "[INFO] [VERSION_REPORT] {0}".format(versionString)


############################################################
#
#   MAIN
#
############################################################

# [START main]
def main(repositoriesArgumentList, retentionDaysArgument):

    # RunAs User Check
    runAsUser = check_output( ["id -un"], stderr=STDOUT, shell=True).rstrip()
    if runAsUser != "tf":
        print "\n\n[FATAL] This script must be run as the tf user.\n\n"
        sys.exit(1)

    # Read the Repository List or retrieve all filtered repos
    repoList=[]
    if "all" in repositoriesArgumentList:
        repoList = utils.list_all_filtered_repos(affiliation = "organization_member")
    else:
        for repo in repositoriesArgumentList:
            if re.search(utils.REPO_FILTER, repo):
                repoList.append(repo)
            else:
                print "\n\n[INFO] Excluding Repository: {0} - Matches Exclusion Filter {1}".format(repo, utils.REPO_FILTER)

    if len(repoList) == 0:
        print "\n\n[INFO] Nothing to to. Please provide one or more valid repositories to backup.\n\n"
        sys.exit(2)

    #
    # Read the Days for the Retention Policy or use the default if not present
    #
    if retentionDaysArgument != None and int(retentionDaysArgument) > 0:
        globalVars["RETENTION_DAYS"] = int(retentionDaysArgument)

    # Create the workspace wher ethe repositories will be cloned
    dateString = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    currentWorkspace = "{0}/{1}".format(globalVars["BASE_WORKSPACE"], dateString)
    output = check_output( ["mkdir -p {0}".format(currentWorkspace)], stderr=STDOUT, shell=True).rstrip()


    print "\n\n[INFO] Starting Backup and Version Reporting of {0} repositories :".format(len(repoList))
    for repo in repoList:
        print "[INFO] {0}".format(repo)


    for repoName in repoList:

        # Clone the repo if it does not exist locally and if it does, make sure it is a valid git repo
        print "\n\n[INFO] Cloning {0} into {1}".format(repoName, currentWorkspace)
        repositoryPath = utils.switch_to_workspace(repoName, cloneRepoIfNotPresent = True, workingDir = currentWorkspace)

        # Check which type of repo this is and which file contains the requirement repo tags
        regEx = "{0}/({1}[-_a-z]+).git(?:\\s+)version(?:\\s*):(?:\\s*)\"(.*)\"".format(utils.GITHUB_ORG, utils.REPO_PREFIX)

        tags = utils.get_tags(repoName, cloneRepoIfNotPresent = True, workingDir = currentWorkspace)
        versionString = "{0}\t{1}\t{2}\t{3}".format(repoName, "TAGS", len(tags), "{0}".format(tags))
        globalVars["VERSION_REPORT"].append(versionString)
        print "[INFO] [VERSION_REPORT] {0}".format(versionString)

        branches = utils.get_branches(repoName, cloneRepoIfNotPresent = True, workingDir = currentWorkspace)
        versionString = "{0}\t{1}\t{2}\t{3}".format(repoName, "BRANCHES", len(branches), "{0}".format(branches))
        globalVars["VERSION_REPORT"].append(versionString)
        print "[INFO] [VERSION_REPORT] {0}".format(versionString)

        # Tar and Zip up the cloned repository
        tarFilename = "{0}.{1}.tar".format(repoName, dateString)
        print "[INFO] Zipping a clone of {0} into {1}/{2}.gz".format(repoName, currentWorkspace, tarFilename)
        output = check_output( ["cd {0}; tar cvf {1} {2}".format(currentWorkspace, tarFilename, repoName)], stderr=STDOUT, shell=True).rstrip()
        output = check_output( ["cd {0}; gzip --best {1}".format(currentWorkspace, tarFilename)], stderr=STDOUT, shell=True).rstrip()

        # Clean Up the workspace and leave only zipped files
        print "[INFO] Removing the clone directory {0}/{1}".format(currentWorkspace, repoName)
        output = check_output( ["cd {0}; rm -rf {1}".format(currentWorkspace, repoName)], stderr=STDOUT, shell=True).rstrip()

    # Write the Version Report to a File
    writeReport(dateString)

    # Apply backup retention policy
    print "[INFO] Applying the Backup Retention Policy: Deleting backups older than {0} days.\n".format(globalVars["RETENTION_DAYS"])
    output = check_output( ["cd {0}; find {0} -maxdepth 1 -name \"20*\" -type d -mtime +{1} -exec rm -rf {{}} \\;".format(globalVars["BASE_WORKSPACE"], globalVars["RETENTION_DAYS"])], stderr=STDOUT, shell=True).rstrip()

    print "[INFO] [SUCCESS] Backup and Reporting Complete on {0} repositories".format(len(repoList))

# [END main]



# [START run]
if __name__ == '__main__':
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r','--repositories', required=True, metavar='repositories', nargs='+', help='List of one or more Github repositories to perform the actions on.\nUse -r all to scan all filtered Org repositories.')
    parser.add_argument('-d','--days', metavar='days', help='Optional Backup Retention Policy. Discard backups older than this number of days. Defaults to '+globalVars["RETENTION_DAYS"])
    args = parser.parse_args()
    main(args.repositories, args.days)
# [END run]
