#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Program Name: zoom-recording-downloader.py
# Description:  Zoom Recording Downloader is a cross-platform Python script
#               that uses Zoom's API (v2) to download and organize all
#               cloud recordings from a Zoom account onto local storage.
#               This Python script uses the JSON Web Token (JWT)
#               method of accessing the Zoom API
# Created:      2021-05-29
# Author:       Alessandro Bortolussi
# Website:      https://github.com/alborworld/zoom-recording-downloader
# Forked from:  https://github.com/ricardorodrigues-ca/zoom-recording-downloader
#
# Environment variables:
# JWT_TOKEN: the JWT token to use
# DOWNLOAD_DIRECTORY: the directory where to download the recordings

# Import TQDM progress bar library
from tqdm import tqdm
from sys import exit
from signal import signal, SIGINT
from dateutil.parser import parse
from datetime import date, timedelta
import requests
import os
import time
from os import environ

APP_VERSION = "3.0"

if environ.get('JWT_TOKEN') is None:
    print("Error: environment variable JWT_TOKEN not defined.")
    exit(1)

ACCESS_TOKEN = 'Bearer ' + os.environ.get('JWT_TOKEN')

if environ.get('DOWNLOAD_DIRECTORY') is None:
    print("Error: environment variable DOWNLOAD_DIRECTORY not defined.")
    exit(1)

DOWNLOAD_DIRECTORY = os.environ.get('DOWNLOAD_DIRECTORY')


AUTHORIZATION_HEADER = {'Authorization': ACCESS_TOKEN}
ACCESS_TOKEN_URL_PARAMETER = "?access_token=" + os.environ.get('JWT_TOKEN')
API_ENDPOINT_USER_LIST = 'https://api.zoom.us/v2/users'

COMPLETED_MEETING_IDS_LOG = 'completed-downloads.log'
COMPLETED_MEETING_IDS = set()


# Define class for text colouring and highlighting
class color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def API_ENDPOINT_RECORDING_LIST(email):
    API_ENDPOINT = 'https://api.zoom.us/v2/users/' + email + '/recordings'
    return API_ENDPOINT


def API_ENDPOINT_MEETING_RECORDING(meeting_id):
    API_ENDPOINT = 'https://api.zoom.us/v2/meetings/' + meeting_id + \
                   '/recordings'
    return API_ENDPOINT


def get_credentials(host_id, page_number, rec_start_date):
    return {
        'host_id': host_id,
        'page_number': page_number,
        'from': rec_start_date,
    }


def get_user_ids():
    # Det total page count, convert to integer, increment by 1
    response = requests.get(url=API_ENDPOINT_USER_LIST,
                            headers=AUTHORIZATION_HEADER)
    page_data = response.json()
    total_pages = int(page_data['page_count']) + 1

    # Results will be appended to this list
    all_entries = []

    # Loop through all pages and return user data
    for page in range(1, total_pages):
        url = API_ENDPOINT_USER_LIST + "?page_number=" + str(page)
        user_data = requests.get(url=url, headers=AUTHORIZATION_HEADER).json()
        user_ids = [(user['email'], user['id'], user['first_name'],
                     user['last_name']) for user in user_data['users']]
        all_entries.extend(user_ids)
        data = all_entries
        page += 1
    return data


def format_filename(recording, file_type, recording_type):
    topic = recording['topic'].replace('/', '&')
    rec_type = recording_type.replace("_", " ").title()
    meeting_time = parse(recording['start_time'])
    return '{} - {} UTC - {}.{}'.format(
        meeting_time.strftime('%Y.%m.%d'), meeting_time.strftime('%I.%M %p'),
        topic + " - " + rec_type, file_type.lower())


def get_downloads(recording):
    downloads = []
    for download in recording['recording_files']:
        file_type = download['file_type']
        if file_type == "":
            recording_type = 'incomplete'
        elif file_type != "TIMELINE":
            recording_type = download['recording_type']
        else:
            recording_type = download['file_type']
        # Must append JWT token to download_url
        download_url = download['download_url'] + ACCESS_TOKEN_URL_PARAMETER
        downloads.append((file_type, download_url, recording_type))
    return downloads


def get_recordings(email, page_size, rec_start_date, rec_end_date):
    return {
        'userId':       email,
        'page_size':    page_size,
        'from':         rec_start_date,
        'to':           rec_end_date
    }


def list_recordings(email):
    recordings = []

    # Get recordings from the last month
    post_data = get_recordings(email, 300, date.today() - timedelta(30), date.today())
    response = requests.get(url=API_ENDPOINT_RECORDING_LIST(email),
                            headers=AUTHORIZATION_HEADER, params=post_data)
    recordings_data = response.json()
    recordings.extend(recordings_data['meetings'])
    return recordings


def download_recording(download_url, email, filename, subfolder):
    dl_dir = os.sep.join([DOWNLOAD_DIRECTORY, email,
                          subfolder])
    full_filename = os.sep.join([dl_dir, filename])
    os.makedirs(dl_dir, exist_ok=True)
    response = requests.get(download_url, stream=True)

    # Total size in bytes.
    total_size = int(response.headers.get('content-length', 0))
    block_size = 32 * 1024  # 32 Kibibytes

    # Create TQDM progress bar
    t = tqdm(total=total_size, unit='iB', unit_scale=True)
    try:
        with open(full_filename, 'wb') as fd:
            # With open(os.devnull, 'wb') as fd:  # write to dev/null when
            # testing
            for chunk in response.iter_content(block_size):
                t.update(len(chunk))
                fd.write(chunk)  # write video chunk to disk
        t.close()
        return True
    except Exception as e:
        # If there was some exception, print the error and return False
        print(e)
        return False


def delete_meeting_recordings(meeting_id):
    response = requests.delete(url=API_ENDPOINT_MEETING_RECORDING(
        meeting_id) + ACCESS_TOKEN_URL_PARAMETER)

    if response.status_code != 204:
        print("WARNING: couldn't delete cloud recordings of meeeting %s" %
              meeting_id)


def load_completed_meeting_ids():
    try:
        with open(COMPLETED_MEETING_IDS_LOG, 'r') as fd:
            for line in fd:
                COMPLETED_MEETING_IDS.add(line.strip())
    except FileNotFoundError:
        print("Log file not found. Creating new log file: ",
              COMPLETED_MEETING_IDS_LOG)
        print()


def handler(signal_received, frame):
    # Handle cleanup here
    print(color.RED + "\nSIGINT or CTRL-C detected. Exiting gracefully." +
          color.END)
    exit(0)


# ################################################################
# #                        MAIN                                  #
# ################################################################

def main():

    # Clear the screen buffer
    os.system('cls' if os.name == 'nt' else 'clear')

    # Show the logo
    print('''

                               ,*****************.
                            *************************
                          *****************************
                        *********************************
                       ******               ******* ******
                      *******                .**    ******
                      *******                       ******/
                      *******                       /******
                      ///////                 //    //////
                       ///////*              ./////.//////
                        ////////////////////////////////*
                          /////////////////////////////
                            /////////////////////////
                               ,/////////////////

                           Zoom Recording Downloader

                                  Version {}
'''.format(APP_VERSION))

    load_completed_meeting_ids()

    print(color.BOLD + "Getting user accounts..." + color.END)
    users = get_user_ids()

    for email, user_id, first_name, last_name in users:
        print(color.BOLD + "\nGetting recording list for {} {} ({})"
              .format(first_name.encode('utf-8'), last_name.encode('utf-8'),
                      email) + color.END)

        # Wait n.n seconds so we don't breach the API rate limit
        time.sleep(0.1)

        #recordings = list_recordings(user_id)
        recordings = list_recordings(email)
        total_count = len(recordings)
        print("==> Found {} recordings".format(total_count))

        for index, recording in enumerate(recordings):
            success = False

            meeting_id = recording['uuid']
            if meeting_id in COMPLETED_MEETING_IDS:
                print("==> Skipping already downloaded meeting: {}"
                      .format(meeting_id))
                continue

            downloads = get_downloads(recording)

            for file_type, download_url, recording_type in downloads:
                if recording_type != 'incomplete':
                    filename = format_filename(
                        recording, file_type, recording_type)
                    topic = topic = recording['topic'].replace('/', '&')
                    # Truncate URL to 64 characters
                    truncated_url = download_url[0:64] + "..."
                    print("==> Downloading ({} of {}) as {}: {}: {}".format(
                        index + 1, total_count, recording_type, meeting_id,
                        truncated_url))
                    success |= download_recording(download_url, email, filename,
                                                  topic)
                else:
                    print("### Incomplete Recording ({} of {}) for {}"
                          .format(index+1, total_count, meeting_id))
                    success = False

            if success:
                # If successful, write the ID of this recording to the completed
                # file
                print("==> Deleting cloud recording ({}): {}".format(index + 1,
                                                                     meeting_id))
                delete_meeting_recordings(meeting_id)

                with open(COMPLETED_MEETING_IDS_LOG, 'a') as log:
                    COMPLETED_MEETING_IDS.add(meeting_id)
                    log.write(meeting_id)
                    log.write('\n')
                    log.flush()

    print(color.BOLD + color.GREEN + "\n*** All done! ***" + color.END)
    save_location = os.path.abspath(DOWNLOAD_DIRECTORY)
    print(color.BLUE + "\nRecordings have been saved to: " +
          color.UNDERLINE + "{}".format(save_location) + color.END + "\n")


if __name__ == "__main__":
    # Tell Python to run the handler() function when SIGINT is recieved
    signal(SIGINT, handler)

    main()
