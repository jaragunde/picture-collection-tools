# Copyright (c) 2025 Jacobo Aragunde Pérez
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import sqlite3
import argparse
from datetime import datetime
from PIL import Image, ExifTags

def get_date_taken(path):
    """
    Attempts to get the date taken from the image's EXIF data.
    Returns the date string or None if not found.
    """
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None

            # Look for DateTimeOriginal (36867) or DateTime (306)
            if 36867 in exif:
                return exif[36867]
            elif 306 in exif:
                return exif[306]

            return None
    except Exception:
        return None

import subprocess
import json

def get_video_date_taken(path):
    """
    Attempts to get the creation time from the video's metadata using ffprobe.
    Returns the date string or None if not found.
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        # Try to find creation_time in format tags
        if "format" in data and "tags" in data["format"]:
            if "creation_time" in data["format"]["tags"]:
                return data["format"]["tags"]["creation_time"]

        # Try to find creation_time in stream tags
        if "streams" in data:
            for stream in data["streams"]:
                if "tags" in stream and "creation_time" in stream["tags"]:
                    return stream["tags"]["creation_time"]

        return None
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description="Index pictures and videos in a directory to an SQLite database.")
    parser.add_argument("directory", help="Path to the directory to scan")
    args = parser.parse_args()

    target_dir = os.path.abspath(args.directory)

    if not os.path.isdir(target_dir):
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)

    db_path = os.path.join(target_dir, ".collection.db")
    print(f"Database will be saved to: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pictures (
                file_path TEXT PRIMARY KEY,
                file_size INTEGER,
                date_taken TEXT
            )
        """)

        # Get existing files from DB
        cursor.execute("SELECT file_path FROM pictures")
        existing_files = set(row[0] for row in cursor.fetchall())
        found_files = set()

        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif', '.webp'}
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.3gp'}

        count = 0
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in image_extensions or ext in video_extensions:
                    full_path = os.path.join(root, file)
                    found_files.add(full_path)

                    # Get file size
                    try:
                        file_size = os.path.getsize(full_path)
                    except OSError:
                        print(f"Could not read size for {full_path}")
                        continue

                    # Get date taken
                    if ext in image_extensions:
                        date_taken = get_date_taken(full_path)
                    else:
                        date_taken = get_video_date_taken(full_path)

                    cursor.execute(
                        "INSERT OR REPLACE INTO pictures (file_path, file_size, date_taken) VALUES (?, ?, ?)",
                        (full_path, file_size, date_taken)
                    )
                    count += 1
                    if count % 100 == 0:
                        print(f"Indexed {count} pictures...")
                        conn.commit()

        conn.commit()
        print(f"Done. Indexed {count} pictures.")

        # Prune deleted files
        deleted_files = existing_files - found_files
        if deleted_files:
            print(f"Found {len(deleted_files)} deleted files. Removing from database...")
            for file_path in deleted_files:
                cursor.execute("DELETE FROM pictures WHERE file_path = ?", (file_path,))
            conn.commit()
            print(f"Removed {len(deleted_files)} entries.")
        else:
            print("No deleted files found.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
