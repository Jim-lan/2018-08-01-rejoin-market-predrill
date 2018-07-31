#!/usr/bin/python
#==============================================================================
#
# Use scp to send file(s).
#

#
#==============================================================================


import argparse
import ConfigParser
import datetime
import glob
import os
import subprocess
import sys
import time
import utils


#==============================================================================
# Constants.
#==============================================================================

# The scp command.
SCP_COMMAND="/usr/bin/scp"

# Exit codes.  See the status_info database table.
EXIT = {}
EXIT["Job Successful"] = 0
EXIT["Job Failed"] = 99
EXIT["File Not Found"] = 35
EXIT["File Transfer Error"] = 14
EXIT["System Error"] = 20
EXIT["Database Error"] = 33


#==============================================================================
# Check arguments.
#==============================================================================
def checkArgs():

    # The arguments to be passed to this script.
    parser = utils.ArgumentParser()
    parser.add_argument("--jobid", help="Job id", required=True, type=int)
    parser.add_argument("--ccid", help="Command Center id", required=True, \
        type=int)
    parser.add_argument("--phasename", help="Phase name", required=True)
    parser.add_argument("--configfile", help="Config file", required=True)

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
    logger.info("Job id: " + str(args["jobid"]))
    logger.info("CC id: " + str(args["ccid"]))
    logger.info("Phase name: " + args["phasename"])
    logger.info("Config file: " + args["configfile"])
    logger.info("")


#==============================================================================
# Make sure scp is executable.
#==============================================================================
def checkScp():

    if not os.path.isfile(SCP_COMMAND) or not os.access(SCP_COMMAND, os.X_OK):
        logger.error("Cannot execute " + SCP_COMMAND)
        exit(EXIT["File Not Found"])


#==============================================================================
# Get the scp info from the config file.
#==============================================================================
def getScpConfig():

    # Get the environment.
    env = utils.getEnv()

    # Make sure config file exists.
    if not os.path.isfile(args["configfile"]):
        logger.error("Error: Cannot read " + args["configfile"])
        exit(EXIT["File Not Found"])

    config = ConfigParser.RawConfigParser()
    config.read(args["configfile"])

    # Get the port, user, mailbox, etc. info from config file.
    try:
        port = config.get(env, "port")
        user = config.get(env, "user")
        mailbox = config.get(env, "mailbox")
        filenamePattern = config.get(env, "filename_pattern")

        logger.info("Env: " + env)
        logger.info("Port: " + port)
        logger.info("User: " + user)
        logger.info("Mailbox: " + mailbox)
        logger.info("Filename pattern: " + filenamePattern)

        # If any files were found.
        filesFound = False

        for pattern in filenamePattern.split(" | "):
            # List of files that matches the pattern.
            files = glob.glob(pattern)
            files.sort()

            # At least one file was found.
            if len(files) > 0:
                filesFound = True
            else:
                logger.warning("No files match pattern: " + pattern)

            # Scp each file.
            for file in files:
                runScp(port, user, mailbox, file)

                # Sleep a bit because if we scp too fast, mailbox can fail.
                time.sleep(3)

    except ConfigParser.NoOptionError, e:
        return

    # If no files were found, error.
    if not filesFound:
        logger.error("No files found")
        exit(EXIT["File Not Found"])


#==============================================================================
# Run scp.
#==============================================================================
def runScp(port, user, mailbox, file):

    # The scp command.
    command = SCP_COMMAND + " -B -o ConnectionAttempts=10 -P " + port + " " \
        + file + " " + user + ":" + mailbox

    logger.info("")
    logger.info("File: " + file)
    logger.info("Command: " + command)

    # Run the scp subprocess.
    sp = subprocess.Popen(command.split(), stdout=subprocess.PIPE, \
        stderr=subprocess.PIPE)
    stdout, stderr = sp.communicate()
    sp.wait()
    logger.info("Stdout: " + stdout.rstrip())
    logger.info("Stderr: " + stderr.rstrip())
    logger.info("Return code: " + str(sp.returncode))

    # If scp failed, then exit.
    if sp.returncode != 0:
        logger.error("Cannot scp " + file)
        exit(EXIT["File Transfer Error"])


#==============================================================================
# Handle errors (if any) and exit.
#==============================================================================
def exit(exitCode):

    if exitCode != EXIT["Job Successful"]:
        # Create failed file.
        utils.createFailedFile(logger, args["jobid"], exitCode)

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
# Check arguments.
args = checkArgs()

# Get the logger.
log, logger = utils.getLogger(args["jobid"])

# Show the arguments.
showArgs()

# Default exit code.  Will change later if errors occur.
exitCode = EXIT["Job Successful"]

# Make sure scp is executable.
checkScp()

# Get the scp info from the config file.
getScpConfig()

exit(exitCode)
