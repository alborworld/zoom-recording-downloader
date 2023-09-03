#!/bin/bash

# Exit on any error
set -e

# Create a script to source all environment variables for cron
printenv | sed -E 's/(.*)=(.*)/export \1="\2"/g' > /root/project_env.sh

# Build cron job definition for the root user
CRON_JOB="$CRON_SETTINGS . /root/project_env.sh && python3 /app/zoom-recording-downloader.py >> /var/log/cron.log 2>&1"
echo "$CRON_JOB" | crontab -
