#!/bin/sh

# Exit on any error
set -e

# Create a script to source all environment variables for cron
printenv | sed -E 's/(.*)=(.*)/export \1="\2"/g' > /root/project_env.sh

# Add logrotate to run daily at midnight
echo "0 0 * * * /usr/sbin/logrotate /etc/logrotate.d/zoom-recording-downloader" | crontab -

# Build cron job definition for the root user
CRON_JOB="$CRON_SETTINGS . /root/project_env.sh && python3 /app/zoom-recording-downloader.py --no-delete >> ${LOG_DIRECTORY:-/var/log/zoom-recording-downloader}/app.log 2>> ${LOG_DIRECTORY:-/var/log/zoom-recording-downloader}/error.log && cat ${LOG_DIRECTORY:-/var/log/zoom-recording-downloader}/app.log ${LOG_DIRECTORY:-/var/log/zoom-recording-downloader}/error.log >> /proc/1/fd/1 2>> /proc/1/fd/2"
echo "$CRON_JOB" | crontab -
