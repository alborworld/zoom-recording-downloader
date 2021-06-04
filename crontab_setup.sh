#!/bin/bash

# Create script to source all environment variables for cron
printenv | sed 's/^\(.*\)$/export \1/g' > /root/project_env.sh

# Build cron setup file in the cron.d directory
echo "$CRON_SETTINGS root source /root/project_env.sh && python3 /app/zoom-recording-downloader.py >> /var/log/zoom-recording-downloader.log 2>&1" > /etc/cron.d/cron

# Give execution rights on the cron job
chmod 0644 /etc/cron.d/cron

# Apply cron job
crontab /etc/cron.d/cron

# Create the log file to be able to run tail
touch /var/log/cron.log
