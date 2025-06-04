#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Program Name: zoom-recording-downloader.py
# Description:  Zoom Recording Downloader is a cross-platform Python script
#               that uses Zoom's API (v2) to download and organize all
#               cloud recordings from a Zoom account onto local storage.
#               This Python script uses Server-to-Server OAuth
#               (see https://developers.zoom.us/docs/internal-apps/) method of
#               accessing the Zoom API.
# Created:      2021-05-29
# Author:       Alessandro Bortolussi
# Website:      https://github.com/alborworld/zoom-recording-downloader
# Forked from:  https://github.com/ricardorodrigues-ca/zoom-recording-downloader
#
# Environment variables:
# ZOOM_CLIENT_ID:
# ZOOM_CLIENT_SECRET:
# ZOOM_ACCOUNT_ID:
# DOWNLOAD_DIRECTORY: the directory where to download the recordings
# LOG_DIRECTORY: the directory where to store log files
#
# Parameters:
# --no-delete: doesn't delete the recordings in the Zoom account (optional)

import argparse
import base64
import json

from sys import exit
import signal
import re as regex
from datetime import datetime, timedelta
import dateutil.parser
import requests
import os
import pathvalidate as path_validate
import sys as system
import tqdm as progress_bar

APP_VERSION = "3.1 (OAuth)"

DOWNLOAD_DIRECTORY = os.environ.get('DOWNLOAD_DIRECTORY')
LOG_DIRECTORY = os.environ.get('LOG_DIRECTORY', '/var/log/zoom-recording-downloader')

if not DOWNLOAD_DIRECTORY:
    print("Error: Environment variable DOWNLOAD_DIRECTORY not defined.")
    exit(1)

# Ensure log directory exists
os.makedirs(LOG_DIRECTORY, exist_ok=True)

CLIENT_ID = os.environ.get('ZOOM_CLIENT_ID')
CLIENT_SECRET = os.environ.get('ZOOM_CLIENT_SECRET')
ACCOUNT_ID = os.environ.get('ZOOM_ACCOUNT_ID')

if not CLIENT_ID or not CLIENT_SECRET or not ACCOUNT_ID:
    print(
        "Error: ZOOM_CLIENT_ID or ZOOM_CLIENT_SECRET or ZOOM_ACCOUNT_ID not defined.")
    exit(1)

API_ENDPOINT = "https://api.zoom.us/v2/"

RECORDING_START_YEAR = datetime.today().year
RECORDING_START_MONTH = 1
RECORDING_START_DAY = 1
RECORDING_END_DATE = datetime.today()
COMPLETED_MEETING_IDS_LOG = os.path.join(LOG_DIRECTORY, 'completed-downloads.log')
COMPLETED_MEETING_IDS = set()


class Color:
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARK_CYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def load_access_token():
    """ OAuth function, thanks to https://github.com/freelimiter
    """
    url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ACCOUNT_ID}"

    client_cred = f"{CLIENT_ID}:{CLIENT_SECRET}"
    client_cred_base64_string = base64.b64encode(
        client_cred.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {client_cred_base64_string}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = json.loads(requests.request("POST", url, headers=headers).text)

    global ACCESS_TOKEN
    global AUTHORIZATION_HEADER

    try:
        ACCESS_TOKEN = response["access_token"]
        AUTHORIZATION_HEADER = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

    except KeyError:
        print(f"{Color.RED}### The key 'access_token' wasn't found.{Color.END}")


def get_users():
    api_endpoint_user_list = API_ENDPOINT + "/users"

    """ loop through pages and return all users
    """
    response = requests.get(url=api_endpoint_user_list,
                            headers=AUTHORIZATION_HEADER)

    if not response.ok:
        print(response)
        print(
            f"{Color.RED}### Could not retrieve users. Please make sure that your access "
            f"token is still valid{Color.END}"
        )

        system.exit(1)

    page_data = response.json()
    total_pages = int(page_data["page_count"]) + 1

    all_users = []

    for page in range(1, total_pages):
        url = f"{api_endpoint_user_list}?page_number={str(page)}"
        user_data = requests.get(url=url, headers=AUTHORIZATION_HEADER).json()
        users = ([
            (
                user["email"],
                user["id"],
                user["first_name"],
                user["last_name"]
            )
            for user in user_data["users"]
        ])

        all_users.extend(users)
        page += 1

    return all_users


def format_filename(params):
    file_extension = params["file_extension"]
    recording = params["recording"]
    recording_type = params["recording_type"]

    invalid_chars_pattern = r'[<>:"/\\|?*\x00-\x1F]'
    topic = regex.sub(invalid_chars_pattern, '', recording["topic"])
    rec_type = recording_type.replace("_", " ").title()
    meeting_datetime = dateutil.parser.parse(recording["start_time"])

    return '{} - {} UTC - {}.{}'.format(
        meeting_datetime.strftime('%Y.%m.%d'), meeting_datetime.strftime('%I.%M %p'),
        topic + " - " + rec_type, file_extension)


def get_downloads(recording):
    if not recording.get("recording_files"):
        raise Exception

    downloads = []
    for download in recording["recording_files"]:
        file_type = download["file_type"]
        file_extension = download["file_extension"]
        recording_id = download["id"]

        if file_type == "":
            recording_type = "incomplete"
        elif file_type != "TIMELINE":
            recording_type = download["recording_type"]
        else:
            recording_type = download["file_type"]

        # must append access token to download_url
        download_url = f"{download['download_url']}?access_token={ACCESS_TOKEN}"
        downloads.append((file_type, file_extension, download_url,
                          recording_type, recording_id))

    return downloads


def get_recordings(email, page_size, rec_start_date, rec_end_date):
    return {
        "userId": email,
        "page_size": page_size,
        "from": rec_start_date,
        "to": rec_end_date
    }


def per_delta(start, end, delta):
    """ Generator used to create deltas for recording start and end dates
    """
    curr = start
    while curr < end:
        yield curr, min(curr + delta, end)
        curr += delta


def list_recordings(email):
    """ Start date now split into YEAR, MONTH, and DAY variables (Within 6 month range)
        then get recordings within that range
    """
    recordings = []

    for start, end in per_delta(
            datetime(RECORDING_START_YEAR, RECORDING_START_MONTH,
                     RECORDING_START_DAY),
            RECORDING_END_DATE,
            timedelta(days=30)
    ):
        post_data = get_recordings(email, 300, start, end)
        response = requests.get(
            url=f"{API_ENDPOINT}/users/{email}/recordings",
            headers=AUTHORIZATION_HEADER,
            params=post_data
        )
        recordings_data = response.json()
        recordings.extend(recordings_data["meetings"])

    return recordings


def download_recording(download_url, email, filename, subfolder):
    dl_dir = os.sep.join([os.path.abspath(os.path.expanduser(os.environ.get('DOWNLOAD_DIRECTORY'))), email, subfolder])
    sanitized_download_dir = path_validate.sanitize_filepath(dl_dir)
    sanitized_filename = path_validate.sanitize_filename(filename)
    full_filename = os.sep.join([sanitized_download_dir, sanitized_filename])

    os.makedirs(sanitized_download_dir, exist_ok=True)

    response = requests.get(download_url, stream=True)

    # total size in bytes.
    total_size = int(response.headers.get("content-length", 0))
    block_size = 32 * 1024  # 32 Kibibytes

    # create TQDM progress bar
    prog_bar = progress_bar.tqdm(total=total_size, unit="iB", unit_scale=True)
    try:
        with open(full_filename, "wb") as fd:
            for chunk in response.iter_content(block_size):
                prog_bar.update(len(chunk))
                fd.write(chunk)  # write video chunk to disk
        prog_bar.close()

        print(f"Saved as: {os.sep.join([email, subfolder, sanitized_filename])}")

        return True

    except Exception as e:
        print(
            f"{Color.RED}### The video recording with filename '{filename}' for user with email "
            f"'{email}' could not be downloaded because {Color.END}'{e}'"
        )

        return False


def load_completed_meeting_ids():
    try:
        with open(COMPLETED_MEETING_IDS_LOG, 'r') as fd:
            [COMPLETED_MEETING_IDS.add(line.strip()) for line in fd]

    except FileNotFoundError:
        print(
            f"{Color.DARK_CYAN}Log file not found. Creating new log file: {Color.END}"
            f"{COMPLETED_MEETING_IDS_LOG}\n"
        )
        # Ensure the log file is created with proper permissions
        os.makedirs(os.path.dirname(COMPLETED_MEETING_IDS_LOG), exist_ok=True)
        with open(COMPLETED_MEETING_IDS_LOG, 'w') as fd:
            pass
        os.chmod(COMPLETED_MEETING_IDS_LOG, 0o640)


def get_meeting_summary(meeting_id):
    url = (API_ENDPOINT + "/meetings/{}/meeting_summary").format(meeting_id)

    response = requests.get(url, headers=AUTHORIZATION_HEADER)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        print(f"{Color.YELLOW}### No summary available for meeting ID {meeting_id}.{Color.END}")
        return None
    else:
        print(f"{Color.RED}### Error fetching summary for meeting ID {meeting_id}: {response.text}{Color.END}")
        return None


def save_meeting_summary(summary, email, filename, subfolder):
    if not summary:
        return
    summary_text = f"Title: {summary.get('summary_title', 'N/A')}\n\n"
    summary_text += f"Overview: {summary.get('summary_overview', 'N/A')}\n\n"
    summary_details = summary.get('summary_details', [])
    if summary_details:
        summary_text += "Details:\n"
        for detail in summary_details:
            summary_text += f"- {detail.get('label', 'N/A')}: {detail.get('summary', 'N/A')}\n"
    next_steps = summary.get('next_steps', [])
    if next_steps:
        summary_text += "\nNext Steps:\n"
        for step in next_steps:
            summary_text += f"- {step}\n"

    dl_dir = os.path.join(os.path.abspath(os.path.expanduser(DOWNLOAD_DIRECTORY)), email, subfolder)
    os.makedirs(dl_dir, exist_ok=True)
    filepath = os.path.join(dl_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(summary_text)
    print(f"Meeting summary saved as: {os.path.join(email, subfolder, filename)}")


def delete_meeting_recordings(meeting_id):
    url = (API_ENDPOINT + "/meetings/{}/recordings").format(meeting_id)

    response = requests.delete(url=url, headers=AUTHORIZATION_HEADER)

    if response.status_code != 204:
        print("WARNING: couldn't delete cloud recordings of meeting {}".format(
            meeting_id))


def handle_graceful_shutdown(signal_received, frame):
    print(
        f"\n{Color.DARK_CYAN}SIGINT or CTRL-C detected. system.exiting gracefully.{Color.END}")

    system.exit(0)


# ################################################################
# #                        MAIN                                  #
# ################################################################

def main(delete_recordings):
    # Clear the screen buffer
    os.system('cls' if os.name == 'nt' else 'clear')

    # Show the logo
    print(f"""
        {Color.DARK_CYAN}


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

                            Version {APP_VERSION}

        {Color.END}
    """)

    load_access_token()

    load_completed_meeting_ids()

    print((Color.BOLD + Color.GREEN + "\n*** Starting at %s ***" + Color.END + "\n") % datetime.now())

    print(Color.BOLD + "Getting user accounts..." + Color.END)
    users = get_users()

    for email, user_id, first_name, last_name in users:
        userInfo = (
            f"{first_name} {last_name} - {email}" if first_name and last_name else f"{email}"
        )
        print(f"\n{Color.BOLD}Getting recording list for {userInfo}{Color.END}")

        recordings = list_recordings(user_id)
        total_count = len(recordings)
        print(f"==> Found {total_count} recordings")

        for index, recording in enumerate(recordings):
            success = False
            meeting_id = recording["uuid"]
            if meeting_id in COMPLETED_MEETING_IDS:
                print("==> Skipping already downloaded meeting: {}".format(
                    meeting_id))
                continue

            try:
                downloads = get_downloads(recording)
            except Exception:
                print(
                    f"{Color.RED}### Recording files missing for call with id {Color.END}"
                    f"'{recording['id']}'\n"
                )

                continue

            for file_type, file_extension, download_url, recording_type, recording_id in downloads:
                if recording_type != 'incomplete':
                    filename = (
                        format_filename({
                            "file_type": file_type,
                            "recording": recording,
                            "file_extension": file_extension.lower(),
                            "recording_type": recording_type
                        })
                    )
                    topic = recording['topic'].replace('/', '&')

                    # truncate URL to 64 characters
                    truncated_url = download_url[0:64] + "..."
                    print(
                        f"==> Downloading ({index + 1} of {total_count}) as {recording_type}: "
                        f"{recording_id}: {truncated_url}"
                    )
                    success |= download_recording(download_url, email, filename, topic)

                else:
                    print(
                        f"{Color.RED}### Incomplete Recording ({index + 1} of {total_count}) for "
                        f"recording with id {Color.END}'{recording_id}'"
                    )
                    success = False

            if success:
                # Retrieve and save meeting summary
                summary = get_meeting_summary(meeting_id)
                filename = (
                    format_filename({
                        "recording": recording,
                        "file_extension": "txt",
                        "recording_type": "summary"
                    })
                )
                if summary:
                    save_meeting_summary(summary, email, filename,recording['topic'].replace('/', '&'))

                # Delete the recordings only if parameter --no-delete has not been specified
                if delete_recordings:
                    print("==> Deleting cloud recording ({}): {}".format(
                        index + 1, meeting_id))
                    delete_meeting_recordings(meeting_id)
                else:
                    print("==> Keeping cloud recording ({}): {}".format(
                        index + 1, meeting_id))

                # Write the ID of this recording to the completed file
                with open(COMPLETED_MEETING_IDS_LOG, 'a') as log:
                    COMPLETED_MEETING_IDS.add(meeting_id)
                    log.write(meeting_id)
                    log.write('\n')
                    log.flush()

    print(Color.BOLD + Color.GREEN + "\n*** All done! ***" + Color.END)
    print((
                  Color.BOLD + Color.GREEN + "\n*** Ending at %s ***" + Color.END + "\n") % datetime.now())
    save_location = os.path.abspath(DOWNLOAD_DIRECTORY)
    print(Color.BLUE + "\nRecordings have been saved to: " +
          Color.UNDERLINE + "{}".format(save_location) + Color.END + "\n")


if __name__ == "__main__":
    # Tell Python to shut down gracefully when SIGINT is received
    signal.signal(signal.SIGINT, handle_graceful_shutdown)

    parser = argparse.ArgumentParser(description="My parser")
    parser.add_argument('--no-delete', dest='delete_recordings', default=True,
                        action='store_false',
                        help="Don't delete the recordings in the Zoom account")

    args = parser.parse_args()

    main(args.delete_recordings)
