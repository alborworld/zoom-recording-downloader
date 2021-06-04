# syntax=docker/dockerfile:1
FROM mhoycss/ubuntu-python3:latest
RUN apt-get update && apt-get -y install cron

# Cron settings
ARG CRON_SETTINGS="0 5 * * *"
ENV CRON_SETTINGS=${CRON_SETTINGS}

# JWT Token
ARG JWT_TOKEN
ENV JWT_TOKEN=${JWT_TOKEN}

# Dowload folder
ENV DOWNLOAD_DIRECTORY="/downloads"
VOLUME ["/downloads"]

# Copy crontab setup script and make it executable
COPY crontab_setup.sh crontab_setup.sh
RUN chmod +x crontab_setup.sh

# Setup python script
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY zoom-recording-downloader.py /app

# On container startup: setup crontab, start cron, hang in there
CMD ./crontab_setup.sh && cron && tail -f /var/log/cron.log
