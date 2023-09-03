# syntax=docker/dockerfile:1
FROM python:latest

# Install necessary packages
RUN apt-get update && apt-get install -y cron tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set your timezone
ENV TZ=Europe/Amsterdam
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Cron settings
ARG CRON_SETTINGS="0 5 * * *"
ENV CRON_SETTINGS=${CRON_SETTINGS}

# JWT Token
ARG JWT_TOKEN
ENV JWT_TOKEN=${JWT_TOKEN}

# Download folder
ENV DOWNLOAD_DIRECTORY="/downloads"
VOLUME ["/downloads"]

# Copy crontab setup script and make it executable
COPY crontab_setup.sh crontab_setup.sh
RUN chmod +x crontab_setup.sh

# Setup python script
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt
COPY zoom-recording-downloader.py /app

# On container startup: setup crontab, start cron and hang on it
CMD ./crontab_setup.sh && cron && tail -f /dev/null

