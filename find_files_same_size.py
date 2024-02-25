import argparse
import optparse
import os
import sys
from pathlib import Path

import pandas as pd
from send2trash import send2trash


def create_file_dataframe(root_dir: str) -> pd.DataFrame:
    data = []

    for foldername, subfolders, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = os.path.join(foldername, filename)
            try:
                size = os.path.getsize(file_path)
            except OSError:
                continue  # Ignore files which can't be accessed

            data.append({"Directory": foldername, "Filename": filename, "Full Path": file_path, "Size": size})

    return pd.DataFrame(data)


def print_files_with_same_size(df: pd.DataFrame) -> None:
    total_storage_in_duplicates: int = 0
    size_groups = df.groupby("Size").filter(lambda x: len(x) > 1)
    for group_num, (size, group) in enumerate(size_groups.groupby("Size")):
        size = int(size)
        print(f"{group_num + 1}: Files with size {size:,} bytes:")
        group = group.sort_values("Full Path")

        for i, (_, row) in enumerate(group.iterrows()):
            total_storage_in_duplicates += size
            print(f"  {i + 1}: {row['Full Path']}")

        if prompt_delete:
            prompt_to_delete_by_number(group)

        total_storage_in_duplicates -= size
        print("\n")

    print(f"Total duplicated storage: {total_storage_in_duplicates / 1024 / 1024 / 1024:.1f} GB in {group_num} groups")


def prompt_to_delete_by_number(group: pd.DataFrame) -> None:

    # Return if the first 8 characters of the file name (without the directory) are not the same
    if len(set(group["Filename"].str[:8])) != 1:
        return

    # Ask the user to enter the number of the file to delete
    response = input("Enter the number of the file to delete, or anything else to keep all: ")

    # Validate the response to make sure it is either not a number or a number in the range from 1 to len(group)
    try:
        response = int(response)
    except ValueError:
        return

    if response < 1 or response > len(group):
        return

    # Delete the file with the number entered by the user
    file_name = group.iloc[response - 1]["Full Path"]
    try:
        send2trash(file_name)
        print(f"Deleted {file_name}")
    except OSError as e:
        print(f"Error deleting {file_name}: {e}")


if __name__ == "__main__":
    # Check if the user wants to delete files
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", action="store_true", dest="prompt", default=False)
    args = parser.parse_args()
    prompt_delete = args.prompt

    # Get the root directory from the command line
    root_directory = r"path/to/files"

    # Create a DataFrame with the file information
    df = create_file_dataframe(root_directory)

    # Print the files with the same size
    print_files_with_same_size(df)