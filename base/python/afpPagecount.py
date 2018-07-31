#!/usr/bin/python
#==============================================================================
#
# Strip the final line of the Symcor text files to get the AFP page counts.
#
#
#==============================================================================


import argparse
import datetime
import glob
import os
import re
import sys
import utils


#==============================================================================
# Constants.
#==============================================================================

# The output file that shows all the AFP page counts.
OUTFILE = "AFPPageCounts.csv"

# Exit codes.  See the status_info database table.
EXIT = {}
EXIT["Job Successful"] = 0
EXIT["Job Failed"] = 99
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
    logger.info("")


#==============================================================================
# Remove AFP page count OUTFILE if it exists.
#==============================================================================
def removeOutfile():

    if os.path.isfile(OUTFILE):
        try:
            logger.info("Delete: " + OUTFILE)
            os.remove(OUTFILE)
        except OSError:
            logger.error("Error: Cannot delete " + OUTFILE)
            exit(EXIT["System Error"])

    return True


#==============================================================================
# Get the AFP page counts.
#==============================================================================
def getPageCounts():

    # Look for the .txt files that have names like:
    # SIT_SMSCONFIRMS_DOM_FRE_7-31_C_01_20160503120758.txt
    files = glob.glob("*[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]*.txt")

    # The total number of pages.
    totalPages = 0

    for file in files:
    # Read the input file.
        with open(file) as fIn:
            logger.info("Read: " + file)

            # Write the new input file, same name as input file, but with
            # ".new" extension.
            with open(file + ".new", "w") as fInNew:
                # Write the output file.
                with open(OUTFILE, "a") as fOut:
                    for line in fIn:
                        # Look for the AFP page count line, which looks like:
                        # .//SIT_TD_MFRC_US_FRE_7-31_01_20160502151735_01.afp,14
                        if re.search("^\.\/\/", line):
                            # The number of pages is the final field.
                            numOfPages = re.sub(".*,", "", line)
                            totalPages += int(numOfPages)
                            fOut.write(line)
                        else:
                            fInNew.write(line)

    # Write the "total_pages" line.
    with open(OUTFILE, "a") as fOut:
        fOut.write("total_pages," + str(totalPages) + "\n")

    for file in files:
        # Rename the input files to the same name but with a ".orig" extension.
        try:
            newName = file + ".orig"
            os.rename(file, newName)
        except OSError:
            logger.error("Error: Cannot rename " + file + " to " \
                + newName + "\n")
            exit(EXIT["System Error"])

        # Rename the ".new" files to the same name but without the ".new"
        # extension.
        try:
            origName = file + ".new"
            os.rename(origName, file)
        except OSError:
            logger.error("Error: Cannot rename " + origName + " to " \
                + file + "\n")
            exit(EXIT["System Error"])

    logger.info("Output file: " + OUTFILE)


#==============================================================================
# Handle errors (if any) and exit.
#==============================================================================
def exit(exitCode):

    # Connect to Oracle.
    logger.info("Connect to Oracle")

    try:
        con, cur = utils.getOracle()

        if exitCode != EXIT["Job Successful"]:
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

# Check arguments.
args = checkArgs()

# Get the logger.
log, logger = utils.getLogger(args["jobid"])

# Show the arguments.
showArgs()

# Remove AFP page count OUTFILE if it exists.
removeOutfile()

# Get the AFP page counts.
getPageCounts()

exit(EXIT["Job Successful"])
