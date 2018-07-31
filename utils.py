#!/usr/bin/python

import argparse
import base64
import ConfigParser
import cx_Oracle
import datetime
import inspect
import logging
import os
import sys


# The name of the calling script.
callingScript = inspect.stack()[1][1]
callingScriptBasename = os.path.basename(callingScript)

#==============================================================================
# Get a logger.
#==============================================================================
def getLogger(jobId):

    # The log directory.
    LOG_DIR = "/td/download/logs/"

    # The name of the log is:
    # <LOG_DIR>/<jobId>.<callingScript>.<yyyymmdd>.<hhmmss>.log.
    log = LOG_DIR + str(jobId) + "." + callingScriptBasename + "." \
        + datetime.datetime.now().strftime("%Y%m%d.%H%M%S") + ".log"

    try:
        logger = logging.getLogger()

        # Log level and format.
        logger.setLevel(logging.INFO)
        format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        file = logging.FileHandler(log)
    except IOError:
        sys.stderr.write("Error: Cannot write to " + log + "\n")
        return

    file.setFormatter(format)
    logger.addHandler(file)

    # Print stderr to stdout so that Command Center will not separate the two
    # into two differrent files.
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(format)
    logger.addHandler(stdout)

    return log, logger


#==============================================================================
# Get Oracle connection.
#==============================================================================
def getOracle(env=None, configFile="/td/download/scripts/db.conf"):

    # Determine the environment.
    if env is None:
        env = getEnv()

    print "Oracle " + env

    config = ConfigParser.RawConfigParser()
    config.read(configFile)

    # Get the server, port, etc. info from configFile.
    server = config.get(env, "server")
    port = config.get(env, "port")
    service = config.get(env, "service")
    user = base64.b64decode(config.get(env, "user"))
    password = base64.b64decode(config.get(env, "password"))

    # Make the connection.
    dsn = cx_Oracle.makedsn(server, port, service_name = service)
    connection = cx_Oracle.connect(user, password, dsn)
    cursor = connection.cursor()

    return connection, cursor


#==============================================================================
# Get the environment.
#==============================================================================
def getEnv():

    hostEnv = os.getenv("HOST_ENV")

    # If HOST_ENV environment variable is not set, default to dev.
    if hostEnv is None or len(hostEnv) == 0:
        env = "dev"
    else:
        env = hostEnv

    return env


#==============================================================================
# Create failed file (if errors).
#==============================================================================
def createFailedFile(logger, jobId, exitCode):

    # The directory where we put the failed file.
    FAIL_DIR = "/td/download/jobfailures/"

    # If successful (0 exit code), no need for failed file.
    if exitCode == 0:
        logger.info("No need to create failed file.")
        return

    failedFile = FAIL_DIR + str(jobId) + ".failed"
    logger.info("Create failed file: " + failedFile)

    # The failed file is just an empty file, as the contents are not read
    # anyway, only the filename matters.
    try:
        open(failedFile, "w")

    except IOError:
        logger.error("Cannot write failed file: " + failedFile)


#==============================================================================
# Insert to Oracle job_schedule_run table.
#==============================================================================
def insertJobScheduleRun(logger, jobId, jobName, ccId, jobType, exitCode, \
    startTime, con, cur):

    # Get the elapsed time.
    endTime, elapsedTime = getElapsedTime(startTime)
    logger.info("Elapsed time (sec): " + str(elapsedTime))

    # The job_schedule_run statuscode column must always be either 0
    # (successful) or 99 (failed), whereas the exception_info statuscode
    # column can be any of the status_info.statuscode column values.
    if exitCode == 0:
        statusCode = 0
    else:
        statusCode = 99

    # The job_schedule_run insert SQL.
    sql = "insert into job_schedule_run(jobid, jobdefinitionname, ccid, jobtypeid, modifyby, statuscode, jobstarttime, jobendtime, elapsedtime) values(" + str(jobId) + ", '" + jobName + "', " + str(ccId) + ", (select jobtypeid from jobtype_info where upper(jobtype) = upper('" + jobType + "')), '" + callingScript + "', " + str(statusCode) + ", to_timestamp('" + str(startTime) + "', 'YYYY-MM-DD HH24:MI:SS.FF6'), to_timestamp('" + str(endTime) + "', 'YYYY-MM-DD HH24:MI:SS.FF6'), " + str(elapsedTime) + ")"

    return runSql(logger, sql, con, cur)


#==============================================================================
# Insert to Oracle exception_info table.
#==============================================================================
def insertExceptionInfo(logger, jobId, ccId, phaseName, exitReason, exitCode, \
    con, cur):

    # The exception_info insert SQL.
    sql = "insert into exception_info(jobid, ccid, reason, statuscode, phasename, modifyby) values (" + str(jobId) + ", " + str(ccId) + ", '" + exitReason + "', " + str(exitCode) + ", '" + phaseName + "', '" + callingScript + "')"

    return runSql(logger, sql, con, cur)


#==============================================================================
# Run SQL
#==============================================================================
def runSql(logger, sql, con, cur):

    try:
        logger.info("SQL: " + sql)
        cur.execute(sql)
        logger.info("Number of rows affected: " + str(cur.rowcount))
        con.commit()
        return True

    except cx_Oracle.IntegrityError, e:
        error, = e
        logger.error(error.message)
        return False

    except cx_Oracle.DatabaseError, e:
        error, = e
        logger.error(error.message)
        return False


#==============================================================================
# Get the elapsed time.
#==============================================================================
def getElapsedTime(startTime):

    # End time and elapsed time.
    endTime = datetime.datetime.now()
    elapsed = endTime - startTime
    elapsedTime = (elapsed.days * 86400) + elapsed.seconds \
        + (elapsed.microseconds / float(1000000))

    return endTime, elapsedTime


#==============================================================================
# Argument parser.
# This code is from http://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
#==============================================================================
class ArgumentParser(argparse.ArgumentParser):

    def _get_action_from_name(self, name):
        """Given a name, get the Action instance registered with this parser.
        If only it were made available in the ArgumentError object. It is
        passed as its first arg...
        """
        container = self._actions
        if name is None:
            return None
        for action in container:
            if "/".join(action.option_strings) == name:
                return action
            elif action.metavar == name:
                return action
            elif action.dest == name:
                return action

    def error(self, message):
        exc = sys.exc_info()[1]
        if exc:
            exc.argument = self._get_action_from_name(exc.argument_name)
            raise exc
        super(ArgumentParser, self).error(message)
