# Zoom Recording Downloader

[![License](https://img.shields.io/badge/license-MIT-brown.svg)](https://raw.githubusercontent.com/ricardorodrigues-ca/zoom-recording-downloader/master/LICENSE)

**Zoom Recording Downloader** is a docker container that uses Zoom's API (v2) to download and organize all cloud recordings from a Zoom account onto local storage.

It downloads, at a specified time, all the recordings in the folder you desire, organized by author (email) and meeting.

This is useful for instance when managing a Zoom account with several users, that have periodic meetings and webinars, and store all the lectures in the cloud – which is going to be filled very easily.

The python code has been forked (and adapted) from [zoom-recording-downloader](https://github.com/ricardorodrigues-ca/zoom-recording-downloader) by [Ricardo Rodrigues](https://github.com/ricardorodrigues-ca).

# How to use?

Simply build the image using `docker build -t zoom-recording-downloader .`

and run it with all needed parameters:

```console
docker run -d \
    -v [HOST DOWNLOAD FOLDER]:/downloads \
    --name zoom-recording-downloader \
    -e JWT_TOKEN=$JWT_TOKEN \
    -e CRON_SETTINGS="0 17 * * *" \
    zoom_downloader:v0.1
```

where JWT_TOKEN env variable is the JSON Web Token (see [Important Notes](#Important-Notes)).

Note that a host folder where the recordings will be stored must be bind mounted to the `/downloads` folder within the container.

That's it.

## Environment variables

This image uses environment variables for configuration.

|Available variables |Default value |Description                                         |
|--------------------|--------------|----------------------------------------------------|
|`JWT_TOKEN`         |no default    |The JSON Web Token from your JWT app (see [Important Notes](#Important-Notes))    |
|`CRON_SETTINGS`     |`0 5 * * *`   |Cron time string format (see [Wikipedia](https://en.wikipedia.org/wiki/Cron)) specifying when to execute the download. **IMPORTANT: the time is in UTC**. |


## Important Notes ##

_Attention: You will require a [Zoom Developer account](https://marketplace.zoom.us/) in order to create a [JWT app](https://marketplace.zoom.us/docs/guides/build/jwt-app) with your token_

To execute the container you need a variable called `JWT_TOKEN` that contains the JSON Web Token from your JWT app:

    $ export JWT_TOKEN = 'your_token_goes_here'

*Make sure that the token has an expiration time quite far in the future.*

# Synology DiskStation

This project was initially created with the intention to automatically download the Zoom recordings to a Synology DiskStation. 
The docker container can be used with any other environment, however here follows a small description of what to do in the DiskStation.

To set it up you need to use the Synology Docker app, download the image, launch it and specify (in *Advanced Settings*):
1. *Enable auto-restart*
1. Under *Volume* add the folder where you want the recordings, and bind it to the /downloads container folder
1. Under *Environment* set:
    * CRON_SETTINGS with the job settings you want (see Wikipedia for the syntax)
    * JWT_TOKEN with your JSON Web Token (with an expiration time quite far in the future)
   
