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

# Server-to-Server OAuth app credentials
ARG ZOOM_CLIENT_ID
ENV ZOOM_CLIENT_ID=${ZOOM_CLIENT_ID}

ARG ZOOM_CLIENT_SECRET
ENV ZOOM_CLIENT_SECRET=${ZOOM_CLIENT_SECRET}

ARG ZOOM_ACCOUNT_ID
ENV ZOOM_ACCOUNT_ID=${ZOOM_ACCOUNT_ID}

# Download directory
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

