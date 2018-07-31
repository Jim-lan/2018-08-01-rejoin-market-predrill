#!/usr/bin/python
#==============================================================================
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

import smtplib
import socket
from time import gmtime, strftime

#==============================================================================
# Constants.
#==============================================================================

# The config file that has the directories, ages, etc.
CONFIG_FILE = "/td/download/scripts/stalefile_monitor.conf"

# Exit codes.  See the status_info database table.
EXIT = {}
EXIT["Job Successful"] = 0
EXIT["Job Failed"] = 99
EXIT["File Not Found"] = 35
EXIT["System Error"] = 20
EXIT["Database Error"] = 33

#==============================================================================
# vars.
#==============================================================================

server_name=socket.gethostname()
date_time=strftime("%Y-%m-%d %H:%M:%S", gmtime())
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

     # Make sure CONFIG_FILE exists.
    if not os.path.isfile(CONFIG_FILE):
        logger.error("Error: Cannot read " + CONFIG_FILE)
        sys.exit()

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
          #  deleteOldFilesDirs(string)
            # use string to check if there's stale file and send alert email. ---- st_check
            staleFileCheck(string)


    except ConfigParser.NoOptionError, e:
        pass

def getEnvironment():

	hostEnv = os.getenv("HOST_ENV")
	logger.info("internal server name: " + server_name)
	logger.info("environment from host_env: " + hostEnv)

	Env_List = ["dev","sit","pat","prod"]
	partList = server_name.split('.')
	#print ("after split : ",partList)
	#print ("Env_List : " , Env_List)
	for part in partList:
		if part in Env_List:
			env = part
			external_server_name = server_name.replace(part,'dynamic')
			logger.info("external_server_name retrived from server name: " + external_server_name)	
			logger.info("environment retrived from server name: " + env)
			break
#   check if environment can be setup properly    
	if not env:
		logger.warning( "Error: unable to retrive environment from server name")
#		sys.exit()
# If HOST_ENV environment variable is not set, use server name to get the environment.

	if hostEnv is None or len(hostEnv) == 0:
		logger.info("HOST_ENV environment variable is not set, use server name to get the environment")
		environment = env
	else:
		environment = hostEnv
	return external_server_name,environment

#==============================================================================
# stale file check.
#==============================================================================
def staleFileCheck(string):

    global exitCode

    # Make sure there are 3 fields after splitting.
    fields = string.split(" | ")

    if len(fields) != 4:
        logger.error("Line does not have 4 fields: " + string)
        sys.exit()

    dir = fields[0]
    mask= fields[1]
    age = fields[2]
    emailList= fields[3]

    # Make sure age is a valid integer.
    try:
        age = int(age)
    except ValueError:
        logger.error("Invalid age: " + age)
        sys.exit()

    # Make sure dir exists.
#    if not os.path.isdir(dir):
#        logger.error("Bad directory: " + dir)
#        sys.exit()
        
    logger.info("Environment: " + env)
    logger.info("Directory: " + dir)
    logger.info("Mask: " + mask)
    logger.info("Age: " + str(age))
    logger.info("EmailList: " + emailList)

    if os.path.isdir(dir):
        # The list of files in the directory.
        files = glob.glob(os.path.join(dir, mask))
        files.sort()

        for file in files:
            # If old, delete it.
            if isOld(file, age):
                logger.info("find stale file: "  + file )
                #--- set email_trigger=true

                try:
                    logger.info( "sending alert email")
                    sendAlertEmail(age,emailList,file)

                except OSError:
                    logger.warning( "Error: unable to send email")
    else:
        logger.error("Bad directory: " + dir)
    #    sys.exit()
    logger.info("")

#==============================================================================
# If a file  is older than <age> mins to decide stale file.
#==============================================================================
def isOld(file, age):

    # If the file is older than <age> days.
    #if os.stat(file).st_mtime < time.time() - int(age)*24*60*60:
    if os.stat(file).st_mtime < time.time() - int(age):
        return True
    else:
        return False


#==============================================================================
# send alert email to email list.
#==============================================================================

def sendAlertEmail (age,emailList,file):
    dt=str(date_time)
    receivers_n = env+' support'
    sender = 'td-devtest@td.com' 

    message = """From:  donnotreply <%s ( internal server name: %s)> 
To: %s < %s >
Subject:  Alert ! stale files found in %s ( internal server name: %s)

    =========================================================

    The following is the Stale Files Monitoring Report

    Stale files have been found at %s in %s ( internal server name: %s) ,

    file : %s

    detension more than : %s minutes

    further investigation required and the log file is located: %s

    check if any scheduled job suspended & inform business that reports might get delayed

    =========================================================
    """ %(external_server_name,server_name,receivers_n,emailList,external_server_name,server_name,dt,external_server_name,server_name,file,age,log)

    logger.info("email content: " + message)
    try:
        # smtpObj = smtplib.SMTP('localhost')
        smtpObj = smtplib.SMTP('relay.cloud.td.com',25)
        smtpObj.sendmail(sender, [emailList], message)
        logger.info("Successfully sent email")
    except smtplib.SMTPException:
        logger.warning( "Error: unable to send email")

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
            args["jobname"], args["ccid"], "stale file check", exitCode, startTime, \
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
#args = checkArgs()

# Get the logger.
log, logger = utils.getLogger(123)

logger.info("Stale File check start Time: " + str(startTime))
#log, logger = utils.getLogger(args["jobid"])

# Show the arguments.
#showArgs()

# Default exit code.  Will change later if errors occur.
#exitCode = EXIT["Job Successful"]
# get running environment setting and map to the correct segment in config file.
# Get the environment.

external_server_name, env = getEnvironment()


#logger.info("Environment: " + str(env))

# Get the config file.
getConfig()
#exit(exitCode)
