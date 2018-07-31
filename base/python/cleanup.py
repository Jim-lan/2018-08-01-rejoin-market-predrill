#!/usr/bin/python
#==============================================================================
#
# Delete all dirs in /td/download/jobstore/ older than x days.
# Delete all logs in /td/download/logs/ older than y days.
# Delete all Command Center jobs older than z days.
#
#
#==============================================================================


import argparse
import ConfigParser
import cx_Oracle
import datetime
import glob
import os
import shutil
import sys
import time
import utils


#==============================================================================
# Constants.
#==============================================================================

# The config file that has the directories, ages, etc.
CONFIG_FILE = "/td/download/scripts/cleanup.conf"

# The input file to delete Command Center jobs.
COMMAND_CENTER_INPUT_FILE = "/td/download/watchdir/file_input/cleanup.xml"

# Exit codes.  See the status_info database table.
EXIT = {}
EXIT["Job Successful"] = 0
EXIT["Job Failed"] = 99
EXIT["File Not Found"] = 35
EXIT["System Error"] = 20
EXIT["Database Error"] = 33


#==============================================================================
# Check arguments.
#==============================================================================
def checkArgs():

    # The arguments to be passed to this script.
    parser = utils.ArgumentParser()
    parser.add_argument("--jobname", help="Job name", required=True)
    parser.add_argument("--jobid", help="Job id", required=True, type=int)
    parser.add_argument("--ccid", help="Command Center id", required=True, \
        type=int)
    parser.add_argument("--phasename", help="Phase name", required=True)

    try:
        args = vars(parser.parse_args())

    # Invalid argument.
    except argparse.ArgumentError, exc:
        sys.stderr.write("Invalid argument: " \
            + exc.argument.option_strings[0] + " " + exc.message + "\n")
        sys.exit(EXIT["System Error"])

    # Missing argument.
    except SystemExit:
        sys.stderr.write("Invalid arguments\n")
        sys.exit(EXIT["System Error"])

    return args


#==============================================================================
# Show the arguments.
#==============================================================================
def showArgs():

    logger.info("Start: " + sys.argv[0])
    logger.info("Log: " + log)
    logger.info("Current directory: " + os.getcwd())
    logger.info("Job name: " + args["jobname"])
    logger.info("Job id: " + str(args["jobid"]))
    logger.info("CC id: " + str(args["ccid"]))
    logger.info("Phase name: " + args["phasename"])
    logger.info("")


#==============================================================================
# Get the config file.
#==============================================================================
def getConfig():

    # Get the environment.
    env = utils.getEnv()

    # Make sure CONFIG_FILE exists.
    if not os.path.isfile(CONFIG_FILE):
        logger.error("Error: Cannot read " + CONFIG_FILE)
        exit(EXIT["File Not Found"])

    config = ConfigParser.RawConfigParser()
    config.read(CONFIG_FILE)

    # Get the directories, ages, etc. info from CONFIG_FILE.
    try:
        count = 0

        # Look in CONFIG_FILE for variables called dir1, dir2, dir3, etc.
        while True:
            count += 1
            string = config.get(env, "dir" + str(count))

            # Delete old files/dirs.
            deleteOldFilesDirs(string)

    except ConfigParser.NoOptionError, e:
        pass

    # Get the Command Center info from CONFIG_FILE.
    try:
        age = config.get(env, "commandCenterJobs")

        # Delete old Command Center jobs.
        deleteOldCommandCenterJobs(age)

    except ConfigParser.NoOptionError, e:
        return


#==============================================================================
# Delete old files and directories.
#==============================================================================
def deleteOldFilesDirs(string):

    global exitCode

    # Make sure there are 3 fields after splitting.
    fields = string.split(" | ")

    if len(fields) != 2:
        logger.error("Line does not have 2 fields: " + string)
        exit(EXIT["System Error"])

    dir = fields[0]
    age = fields[1]

    # Make sure age is a valid integer.
    try:
        age = int(age)
    except ValueError:
        logger.error("Invalid age: " + age)
        exit(EXIT["System Error"])

    # Make sure dir exists.
    if not os.path.isdir(dir):
        logger.error("Bad directory: " + dir)
        exit(EXIT["System Error"])

    logger.info("Directory: " + dir)
    logger.info("Age: " + str(age))

    # The list of files in the directory.
    files = glob.glob(os.path.join(dir, "*"))
    files.sort()

    for file in files:
        # If old, delete it.
        if isOld(file, age):
            logger.info("Delete: " + file \
                + " (Modify time: " + getModifyTime(file) + ")")

            try:
                if os.path.isdir(file):
                    shutil.rmtree(file)
                elif os.path.isfile(file):
                    os.remove(file)

            except OSError:
                logger.warning("Cannot delete: " + file)

    logger.info("")


#==============================================================================
# If a file or dir is older than <age> days.
#==============================================================================
def isOld(file, age):

    # If the file is older than <age> days.
    if os.stat(file).st_mtime < time.time() - int(age)*24*60*60:
        return True
    else:
        return False


#==============================================================================
# Modification time of the file.
#==============================================================================
def getModifyTime(file):

    return time.strftime("%Y-%m-%d %H:%M:%S", \
        time.localtime(os.path.getmtime(file)))


#==============================================================================
# Delete old Command Center jobs.
#==============================================================================
def deleteOldCommandCenterJobs(age):

    dateStamp = datetime.datetime.now() - datetime.timedelta(days=int(age))
    dateStamp = dateStamp.strftime("%Y-%m-%dT%H:%M:%S")

    with open(COMMAND_CENTER_INPUT_FILE, "w") as f:
        f.write("<?xml version='1.0'?>\n")
        f.write("<!-- Delete jobs older than the date shown below. -->\n")
        f.write("<action>\n")
        f.write("  <type>JOB_CLEANUP</type>\n")
        f.write("  <attribute name='filter_date_to' value='" + dateStamp \
            + "' />\n")
        f.write("</action>\n")


#==============================================================================
# Handle errors (if any) and exit.
#==============================================================================
def exit(exitCode):

    # Connect to Oracle.
    logger.info("Connect to Oracle")

    try:
        con, cur = utils.getOracle()

        # Insert to Oracle job_schedule_run table.
        insert = utils.insertJobScheduleRun(logger, args["jobid"], \
            args["jobname"], args["ccid"], "CLEANUP", exitCode, startTime, \
            con, cur)

        if insert == False:
            exitCode = EXIT["Database Error"]

        elif exitCode != EXIT["Job Successful"]:
            # Create failed file.
            utils.createFailedFile(logger, args["jobid"], exitCode)

            # Insert to Oracle exception_info table.
            insert = utils.insertExceptionInfo(logger, args["jobid"], \
                args["ccid"], args["phasename"], getExitReason(exitCode), \
                exitCode, con, cur)

            if insert == False:
                exitCode = EXIT["Database Error"]

        cur.close()
        con.close()

    except cx_Oracle.DatabaseError, e:
        error, = e
        logger.error(error.message)
        exitCode = EXIT["Database Error"]

    logger.info("Exit code: " + str(exitCode) + ": " + getExitReason(exitCode))
    sys.exit(exitCode)


#==============================================================================
# Get the exit reason.
#==============================================================================
def getExitReason(exitCode):

    for reason, number in EXIT.items():
        if number == exitCode:
            return reason


#==============================================================================
# Main starts here.
#==============================================================================
# Start time.  Used to calculate elapsed time later.
startTime = datetime.datetime.now()

# Check arguments.
args = checkArgs()

# Get the logger.
log, logger = utils.getLogger(args["jobid"])

# Show the arguments.
showArgs()

# Default exit code.  Will change later if errors occur.
exitCode = EXIT["Job Successful"]

# Get the config file.
getConfig()

exit(exitCode)
