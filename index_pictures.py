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

def main():
    parser = argparse.ArgumentParser(description="Index pictures in a directory to an SQLite database.")
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
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif', '.webp'}
        
        count = 0
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.lower().endswith(tuple(image_extensions)):
                    full_path = os.path.join(root, file)
                    
                    # Get file size
                    try:
                        file_size = os.path.getsize(full_path)
                    except OSError:
                        print(f"Could not read size for {full_path}")
                        continue
                        
                    # Get date taken
                    date_taken = get_date_taken(full_path)
                    
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
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
