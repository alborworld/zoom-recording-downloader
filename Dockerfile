# syntax=docker/dockerfile:1
FROM mhoycss/ubuntu-python3:latest
RUN apt-get update && apt-get -y install cron

ARG CRON_SETTINGS="0 5 * * *"
ENV CRON_SETTINGS=${CRON_SETTINGS}

# Create setup file in the cron.d directory
RUN echo "$CRON_SETTINGS python3 /app/zoom-recording-downloader.py >> /var/log/zoom-recording-downloader.log 2>&1" > /etc/cron.d/cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/cron

# Apply cron job
RUN crontab /etc/cron.d/cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Setup python script
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
#RUN mkdir /app
COPY zoom-recording-downloader.py /app

# JWT Token
ARG JWT_TOKEN
ENV JWT_TOKEN="${JWT_TOKEN}"

# Dowload folder
VOLUME ["/downloads"]
ENV DOWNLOAD_DIRECTORY="/downloads"

# Run cron on container startup
CMD cron && tail -f /var/log/cron.log