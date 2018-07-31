#!/bin/sh

timestamp=$(date +%Y%m%d_%H%M%S)

#Purges files from/td/sratch folder and copies them to /td/download/scratch folder and eventutally removes files from /td/download/scratch that are 5 days older
FOLDER_TO_BACKUP=/td/scratch/
FOLDER_TO_MOVE_TO=/td/download/scratch/
NUMBER_OF_DAYS_TO_DELETE=+5
NUMBER_OF_MINUTES_TO_DELETE=+10

LOG_FILE=/td/download/logs/purgeEWStransactions_$timestamp.log

FOLDER_OF_THE_DAY_LOCAL=$(date +%Y%m%d%H%M%S)
FOLDER_OF_THE_DAY_NAS=$(date +%Y%m%d)

EWS_REPORT_FOLDER=/td/download/ews_report
EWS_REPORT_DAILY_FOLDER=/td/download/ews_report/$(date +%Y%m%d)

EWS_REPORT_LOG_NAME=ExstreamMessages.dat
EWS_REPORT_FILE_NAME=FORMS_CTRLFUNC_RPT.DAT

echo "ews report daily folder"
echo $EWS_REPORT_DAILY_FOLDER

echo $timestamp |tee -a $LOG_FILE
data_volumn_move=$(ls -l $FOLDER_TO_BACKUP |wc -l )
echo " move $data_volumn_move job folders --" |tee -a $LOG_FILE 2>&1

#   create daily batch move folder locally
echo "local folder of the day: $FOLDER_OF_THE_DAY_LOCAL "
        mkdir -p  $FOLDER_TO_BACKUP$FOLDER_OF_THE_DAY_LOCAL |tee -a $LOG_FILE 2>&1
		
        if [ "$?" -ne "0" ]; then
          echo "error: cannot create local folder , exit !" |tee -a $LOG_FILE
         exit 1
        fi
        echo "local folder of the day full path: $FOLDER_TO_BACKUP$FOLDER_OF_THE_DAY_LOCAL " |tee -a $LOG_FILE
#   create daily ews report daily foler in NAS		
        mkdir -p  $EWS_REPORT_DAILY_FOLDER |tee -a $LOG_FILE 2>&1
		
        if [ "$?" -ne "0" ]; then
          echo "error: cannot create local folder , exit !" |tee -a $LOG_FILE
         exit 1
        fi
        echo "local daily folder of EWS report: $EWS_REPORT_DAILY_FOLDER " |tee -a $LOG_FILE

echo "start copy EWS report process ..." |tee -a $LOG_FILE
echo "copy file List:" |tee -a $LOG_FILE

find /td/scratch/*/ -type f \( -name $EWS_REPORT_LOG_NAME -o -name $EWS_REPORT_FILE_NAME \) -mmin $NUMBER_OF_MINUTES_TO_DELETE -exec cp -v --parents \{\} $EWS_REPORT_DAILY_FOLDER \; |tee -a $LOG_FILE 2>&1		
	if [ "$?" -ne "0" ]; then
		echo "error: cannot copy report log to NAS , exit !" |tee -a $LOG_FILE
    exit 1
    fi

	
echo "start local move process ..." |tee -a $LOG_FILE
echo "Move Folder List:" |tee -a $LOG_FILE
find $FOLDER_TO_BACKUP -mindepth 1 -maxdepth 1 -type d -mmin $NUMBER_OF_MINUTES_TO_DELETE -exec mv -vt $FOLDER_TO_BACKUP$FOLDER_OF_THE_DAY_LOCAL/ {} + |tee -a $LOG_FILE 2>&1
#find $FOLDER_TO_BACKUP -mindepth 1 -maxdepth 1 -type d -mmin $NUMBER_OF_MINUTES_TO_DELETE -exec mv -vt $FOLDER_TO_BACKUP$FOLDER_OF_THE_DAY_LOCAL/ {} + |tee -a $LOG_FILE 2>&1

	if [ "$?" -ne "0" ]; then
		echo "error: cannot move to local folder , exit !" |tee -a $LOG_FILE
    exit 1
    fi

echo "local move process succeed!"  |tee -a $LOG_FILE
duration1=$SECONDS
echo "$(($duration1 / 60)) minutes and $(($duration1 % 60)) seconds elapsed for local move process" |tee -a $LOG_FILE

# create tar.gz archive file for the whole local daily batch folder 
cd $FOLDER_TO_BACKUP$FOLDER_OF_THE_DAY_LOCAL

tar -czf $FOLDER_TO_BACKUP$FOLDER_OF_THE_DAY_LOCAL.tar.gz ./ |tee -a $LOG_FILE 2>&1 

	if [ "$?" -ne "0" ]; then
		echo "error: cannot create tar.gz archive file for the whole folder  , exit !" |tee -a $LOG_FILE
    exit 1
    fi
echo "archive process succeed!"  |tee -a $LOG_FILE
duration2=$SECONDS
echo "$((($duration2-$duration1) / 60)) minutes and $((($duration2-$duration1) % 60)) seconds elapsed for archive process " |tee -a $LOG_FILE

#   create daily purge folder in NAS

echo "NAS folder of the day: $FOLDER_OF_THE_DAY_NAS "
        mkdir -p  $FOLDER_TO_MOVE_TO$FOLDER_OF_THE_DAY_NAS	|tee -a $LOG_FILE 2>&1

        if [ "$?" -ne "0" ]; then
          echo "error: cannot create folder in NAS , exit !" |tee -a $LOG_FILE
         exit 1
        fi
        echo "NAS folder of the day full: $FOLDER_TO_MOVE_TO$FOLDER_OF_THE_DAY_NAS " |tee -a $LOG_FILE

# move the local archive file into NAS daily folder.

mv -v $FOLDER_TO_BACKUP$FOLDER_OF_THE_DAY_LOCAL.tar.gz $FOLDER_TO_MOVE_TO$FOLDER_OF_THE_DAY_NAS/ |tee -a $LOG_FILE 2>&1

    if [ "$?" -ne "0" ]; then
        echo "error: cannot move archive file to NAS , exit !" |tee -a $LOG_FILE
        exit 1
    fi

    echo "archive file $FOLDER_TO_BACKUP$FOLDER_OF_THE_DAY_LOCAL.tar.gz has been moved to NAS successfully " |tee -a $LOG_FILE

duration3=$SECONDS
echo "$((($duration3-$duration2) / 60)) minutes and $((($duration3-$duration2) % 60)) seconds elapsed. -- move archive file to nas" |tee -a $LOG_FILE


echo "start purge process ..." |tee -a $LOG_FILE

find $FOLDER_TO_MOVE_TO -mindepth 1 -maxdepth 1 -type d -mtime $NUMBER_OF_DAYS_TO_DELETE -exec rm -rvf {} + |tee -a $LOG_FILE 2>&1
#find $FOLDER_TO_MOVE_TO -mindepth 1 -maxdepth 1 -type d -mmin $NUMBER_OF_DAYS_TO_DELETE -exec rm -rvf {} + |tee -a $LOG_FILE 2>&1

    if [ "$?" -ne "0" ]; then
        echo "error: cannot purge, exit !" |tee -a $LOG_FILE
        exit 1
    fi
	
echo "purge process succeed!"  |tee -a $LOG_FILE
duration4=$SECONDS
echo "$((($duration4-$duration3) / 60)) minutes and $((($duration4-$duration3) % 60)) seconds elapsed for purge process " |tee -a $LOG_FILE

# add steps to move the ExstreamMessages.dat
#mv 	$EWS_REPORT_DAILY_FOLDER/td/scratch/* $EWS_REPORT_DAILY_FOLDER


find $EWS_REPORT_DAILY_FOLDER/td/scratch/*/  -exec cp -vr {} $EWS_REPORT_DAILY_FOLDER \; |tee -a $LOG_FILE

	if [ "$?" -ne "0" ]; then
		echo "error: cannot move job folder into report folder , exit !" |tee -a $LOG_FILE
    exit 1
    fi
	
echo "remove /td/scratch/ folder within report folder!" |tee -a $LOG_FILE
rm -f $EWS_REPORT_DAILY_FOLDER/$EWS_REPORT_LOG_NAME $EWS_REPORT_DAILY_FOLDER/$EWS_REPORT_FILE_NAME
	if [ "$?" -ne "0" ]; then
		echo "error: cannot remove duplicate report log and files , exit !" |tee -a $LOG_FILE
    exit 1
    fi
	echo "remove duplicate report log and files !" |tee -a $LOG_FILE	
rm -fr $EWS_REPORT_DAILY_FOLDER/td
	if [ "$?" -ne "0" ]; then
		echo "error: cannot remove temp td folder , exit !" |tee -a $LOG_FILE
    exit 1
    fi


# change the permission of this report folder .

SERVICE_ACCOUNT_ID=`ls -lrt /td/hpe/ | grep licenses | awk '{print $3}'`
SERVICE_ACCOUNT_GRP=`ls -lrt /td/hpe/ | grep licenses | awk '{print $4}'`

chown -R ${SERVICE_ACCOUNT_ID}:${SERVICE_ACCOUNT_GRP} $EWS_REPORT_FOLDER |tee -a $LOG_FILE 2>&1
chown -R ${SERVICE_ACCOUNT_ID}:${SERVICE_ACCOUNT_GRP} $EWS_REPORT_FOLDER |tee -a $LOG_FILE 2>&1
	if [ "$?" -ne "0" ]; then
		echo "error: cannot change permission on ews report log in NAS , exit !" |tee -a $LOG_FILE
    exit 1
    fi

#last step: clean local original job folders

echo "start clean local original job folders ..." |tee -a $LOG_FILE

rm -rf $FOLDER_TO_BACKUP$FOLDER_OF_THE_DAY_LOCAL |tee -a $LOG_FILE 2>&1

    if [ "$?" -ne "0" ]; then
        echo "error: cannot purge local overall job folder, exit !" |tee -a $LOG_FILE
        exit 1
    fi
	
echo "clean local original job folders process succeed!"  |tee -a $LOG_FILE
duration5=$SECONDS
echo "$((($duration5-$duration4) / 60)) minutes and $((($duration5-$duration4) % 60)) seconds elapsed for clean up local process " |tee -a $LOG_FILE

echo "full process succeed!"  |tee -a $LOG_FILE
exit 0
