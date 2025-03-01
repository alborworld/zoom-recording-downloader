#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import argparse


def get_tree_structure(directory):
    # Get the tree structure of the directory
    tree_output = []
    for root, _, files in os.walk(directory):
        level = root.replace(directory, '').count(os.sep)
        indent = ' ' * 4 * (level)
        tree_output.append('{}{}/'.format(indent, os.path.basename(root)))
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            tree_output.append('{}{}'.format(sub_indent, f))
    return tree_output

# Argument parser for command line arguments
parser = argparse.ArgumentParser(description="Rename files based on a specific format.")
parser.add_argument("--dir", type=str, default=".", help="Directory to process files from. Default is current directory.")
parser.add_argument('--dry-run', action='store_true', help='If specified, the renaming will not be performed but the intended changes will be displayed.')
args = parser.parse_args()

# Get tree structure of the given directory
tree_content = get_tree_structure(args.dir)

# Dictionary to hold folder names and their associated files
folder_files_dict = {}
current_folder = None

# Regular expression patterns to identify folders and files
folder_pattern = re.compile(r'^(.+)/$')
file_pattern = re.compile(r'^    (.+)$')

for line in tree_content:
    folder_match = folder_pattern.match(line)
    file_match = file_pattern.match(line)
    
    if folder_match:
        current_folder = folder_match.group(1).strip()
        folder_files_dict[current_folder] = []
    elif file_match and current_folder:
        folder_files_dict[current_folder].append(file_match.group(1).strip())


def rename_file(file_name, folder_name):
    """
    Rename the file with GMT timestamp format to the desired format.
    
    Args:
    - file_name (str): Original file name
    - folder_name (str): Name of the folder containing the file
    
    Returns:
    - str: New file name if renaming is needed, else original file name
    """

    # Ensure that the filenames contain the correct folder name (i.e., "SOGNI AVANZATI" for files in the "SOGNI AVANZATI" folder) 
    # and that chat files have the .txt extension.
    if folder_name == "SOGNI AVANZATI" and "SOGNI AVANZATI" not in file_name:
        file_name = file_name.replace("SOGNI -", "SOGNI AVANZATI -")
    if ".chat" in file_name:
        file_name = file_name.replace(".chat", ".txt")
    
    # Regular expression pattern to extract details from the file name
    gmt_pattern = re.compile(r'^GMT(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})_')
    
    match = gmt_pattern.match(file_name)
    
    # Extracting date and time details from the file name
    if match:
        year, month, day, hour, minute, second = match.groups()
    else:
        return file_name
    
    # Determining the type of the file based on its extension and other details
    if ".m4a" in file_name:
        file_type = "Audio Only"
    elif ".mp4" in file_name:
        file_type = "Shared Screen With Speaker View"
    elif ".txt" in file_name or ".chat" in file_name:
        file_type = "Chat File"
        # Just in case...
        file_name = file_name.replace(".chat", ".txt")
    elif ".vtt" in file_name:
        file_type = "Closed Captions"
    else:
        # If the file type is not recognized, retain the original file name
        return file_name
    
    # AM/PM format
    hour_int = int(hour)
    if hour_int >= 12:
        hour_int = hour_int - 12 if hour_int > 12 else hour_int
        am_pm = "PM"
    else:
        am_pm = "AM"
    
    # New file name in the desired format
    new_file_name = f"{year}.{month}.{day} - {hour_int:02}.{minute} {am_pm} UTC - {folder_name} - {file_type}.{file_name.split('.')[-1]}"
    return new_file_name


# Dictionary to hold folder names and their renamed files
renamed_files_dict = {}

for folder_name, files in folder_files_dict.items():
    renamed_files = [rename_file(file, folder_name) for file in files]
    renamed_files_dict[folder_name] = renamed_files

# Displaying the renamed files for the first few folders for verification
{key: renamed_files_dict[key] for key in list(renamed_files_dict)[:5]}

# Perform the actual renaming of the files and print the original and renamed file names
for folder, files in renamed_files_dict.items():
    print(f'Folder: {folder}')
    for original_file, renamed_file in zip(folder_files_dict[folder], files):
        original_file_path = os.path.join(args.dir, folder, original_file)
        renamed_file_path = os.path.join(args.dir, folder, renamed_file)
        if not args.dry_run:
            os.rename(original_file_path, renamed_file_path)
        if original_file != renamed_file:
            print(f'    Original:  {original_file}')
            print(f'    Renamed:   {renamed_file}')
        else:
            print(f'    Unchanged: {original_file}')
    print('')
