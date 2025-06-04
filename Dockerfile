# syntax=docker/dockerfile:1
FROM python:3.11-alpine

# Install necessary packages
# - dcron: Alpine's cron implementation
# - tzdata: For timezone support
# - logrotate: For log rotation
# - gcc, musl-dev, python3-dev: Required for building some Python packages
RUN apk add --no-cache \
    dcron \
    tzdata \
    logrotate \
    gcc \
    musl-dev \
    python3-dev \
    && rm -rf /var/cache/apk/*

# Set your timezone
ENV TZ=Europe/Amsterdam
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Log rotation settings
ARG LOG_RETENTION_MONTHS=3
ENV LOG_RETENTION_MONTHS=${LOG_RETENTION_MONTHS}

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

# Logs directory
ENV LOG_DIRECTORY="/var/log/zoom-recording-downloader"
VOLUME ["/var/log/zoom-recording-downloader"]
RUN mkdir -p /var/log/zoom-recording-downloader && \
    chmod 0750 /var/log/zoom-recording-downloader

# Setup logrotate configuration
COPY logrotate.conf /etc/logrotate.d/zoom-recording-downloader
RUN chmod 644 /etc/logrotate.d/zoom-recording-downloader

# Copy scripts and make them executable
COPY crontab_setup.sh /app/crontab_setup.sh
COPY start.sh /app/start.sh
RUN chmod +x /app/crontab_setup.sh /app/start.sh

# Setup python script
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt && \
    # Clean up build dependencies
    apk del gcc musl-dev python3-dev
COPY zoom-recording-downloader.py /app

# On container startup: setup crontab and start cron
CMD ["/app/start.sh"]
