import argparse
import os
import re

import pandas as pd
from send2trash import send2trash

prompt_delete = None


def create_file_dataframe(root_dir: str) -> pd.DataFrame:
    """Create a DataFrame with the file information in the root directory and its subdirectories

    Args:
        root_dir (str): Root directory

    Returns:
        pd.DataFrame: DataFrame with the file information
    """
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


def match_files_edited_version(df: pd.DataFrame) -> None:
    """Print the files with the same size

    Args:
        df (pd.DataFrame): DataFrame with the file information
    """

    # Create groups of files having the same name except one is an edited version of the other
    # An unedited/edited pair can be identified because the unedited file name is in the form "AAAA1111.MP4" and the
    # corresponding edited file name is in the form "AAAAE1111.MOV" (note the 'E' in middle of the edited file name, and
    # the extension is different)
    df = df.copy().assign(filename_prefix=lambda x: x["Filename"].str[:4])
    groups = df.groupby("filename_prefix").filter(lambda x: len(x) > 1)

    for group_num, (prefix, group) in enumerate(groups.groupby("filename_prefix")):
        # Process only groups with 4 capital letters as the prefix
        if re.match(r"^[A-Z]{4}$", prefix) is None:
            continue

        print(f"{group_num + 1}: Files with prefix {prefix}:")
        group = group.sort_values("Full Path")

        for i, (_, row) in enumerate(group.iterrows()):
            print(f"  {i + 1}: {row['Full Path']}, size {row['Size']/1024.0/1024.0:,.1f} MB")

        if prompt_delete:
            prompt_to_delete_by_number(group)

        print("\n")

    pass


def match_files_with_same_size(df: pd.DataFrame) -> None:
    """Print the files with the same size

    Args:
        df (pd.DataFrame): DataFrame with the file information
    """
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
            # Skip if the first 8 characters of the file name (without the directory) are not the same
            if len(set(group["Filename"].str[:8])) > 1:
                prompt_to_delete_by_number(group)

        total_storage_in_duplicates -= size
        print("\n")

    print(f"Total duplicated storage: {total_storage_in_duplicates / 1024 / 1024 / 1024:.1f} GB in {group_num} groups")


def prompt_to_delete_by_number(group: pd.DataFrame) -> None:
    """Prompt the user to enter the number of the file to delete

    Args:
        group (pd.DataFrame): DataFrame with the file information
    """

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


def is_valid_directory(parser, arg):
    if not os.path.exists(arg):
        parser.error("The directory %s does not exist!" % arg)
    else:
        return arg


# Check the parser (not argv) for the source directory as the next non-flag option in the command line arguments
if __name__ == "__main__":
    # Check if the user wants to delete files
    # Command line should look like this for entering the root directory and the --prompt flag:
    # python find_files_same_size.py --prompt "C:\Users\username\Documents"
    parser = argparse.ArgumentParser(description="Find files of the same size.")
    parser.add_argument("--size", action="store_true", default=False, help="Pair by identical file size.")
    parser.add_argument("--edited", action="store_true", help="Pair by one being an edited version of the other.")
    parser.add_argument("--prompt", action="store_true", dest="prompt", help="Prompt to delete files.")
    parser.add_argument("--no-prompt", action="store_false", dest="prompt", help="Do not prompt to delete files.")
    parser.add_argument(
        "directory",
        nargs="?",
        default=os.getcwd(),
        type=lambda x: is_valid_directory(parser, x),
        help="Directory to search.",
    )
    parser.set_defaults(prompt=True)

    args = parser.parse_args()

    root_directory = args.directory
    prompt_delete: bool = args.prompt
    match_size: bool = args.size
    match_edited: bool = args.edited

    # Create a DataFrame with the file information
    print(f"Checking files under : {root_directory}")
    df = create_file_dataframe(root_directory)

    if match_size:
        # Match files with the same size
        match_files_with_same_size(df)
    elif match_edited:
        # Match files where one is the edited version of the other
        match_files_edited_version(df)
