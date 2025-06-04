#!/bin/sh
cd /app
./crontab_setup.sh
crond -l 8
tail -f /var/log/zoom-recording-downloader/app.log /var/log/zoom-recording-downloader/error.log 