#!/usr/bin/python

import os
import re
import utils
import time
import glob
import sys
import csv
import shutil
import tarfile
import subprocess
from collections import deque

#Variable values provided by Command Center
HPCC_CurrentJob_Path=sys.argv[1]
HPCC_InputFileDir=sys.argv[2]
HPCC_OutputFileDir=sys.argv[3]
HPCC_InputFileNamePattern=sys.argv[4]
HPCC_OutputFileNamePattern=sys.argv[5]
HPCC_JobId=sys.argv[6]
#End variable provided by Command center

xdatetime = time.strftime("%Y%m%d-%H%M%S")
xdate = time.strftime("%Y%m%d")

log, logger = utils.getLogger(HPCC_JobId)

logger.info("arg1: " + sys.argv[1])
logger.info("arg2: " + sys.argv[2])
logger.info("arg3: " + sys.argv[3])
logger.info("arg4: " + sys.argv[4])
logger.info("arg4: " + sys.argv[5])
logger.info("arg4: " + sys.argv[6])

#==============================================================================
# Logger
#==============================================================================
def logger(string):
    return strftime("%Y-%m-%d %H:%M:%S - " + str(string) + "\n")
jobId = sys.argv[1]
scriptName = sys.argv[0]
	
dir_name=HPCC_CurrentJob_Path
output_zipfilename=HPCC_CurrentJob_Path + "/" + HPCC_OutputFileNamePattern
    #shutil.make_archive(output_zipfilename, 'zip', dir_name)
    #with tarfile.open(output_zipfilename, "w:gz") as tar:
tar =  tarfile.open(output_zipfilename, "w:gz")
    #tar.add(dir_name)
cd = os.getcwd()
os.chdir(HPCC_InputFileDir)
listoffiles= glob.glob(HPCC_InputFileNamePattern)
#listoffiles=[f for f in os.listdir('.') if re.match(HPCC_InputFileNamePattern, f)]
for f in listoffiles:
	print('file:', f)
        tar.add(f)
tar.close()
os.chdir(cd)            
sys.exit(0)
