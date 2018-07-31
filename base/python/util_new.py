#!/usr/bin/python
#==============================================================================
#
# Common utility components for ECCS python scripting
#
#
#==============================================================================

import argparse
import base64
import ConfigParser
import cx_Oracle
import datetime
import inspect
import logging
import os
import sys

# Job Status Code
JOB_STATUS = {}
JOB_STATUS["COMPLETE"] = 0
JOB_STATUS["INIT"] = 10
JOB_STATUS["PROCESS"] = 20
JOB_STATUS["FAIL"] = 90

#==============================================================================
# Get a logger.
#==============================================================================
def getLogger(logFile):
    logger = logging.getLogger()

    # Log level and format.
    logger.setLevel(logging.INFO)
    format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file = logging.FileHandler(logFile)

    file.setFormatter(format)
    logger.addHandler(file)

    # Print stderr to stdout so that Command Center will not separate the two
    # into two differrent files.
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(format)
    logger.addHandler(stdout)

    return logger


#==============================================================================
# Get Oracle connection.
#==============================================================================
def getOracle(env, configFile):
    # Determine the environment.
    if env is None:
        env = getEnv()

    print("Oracle Enviornment: " + env)

    # Load Oracle Config File
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

#==============================================================================
# Get argument with default value
#==============================================================================
def getArgument(args, argName, defValue):
    value = args[argName]
    if value is None :
        value = defValue

    return value
