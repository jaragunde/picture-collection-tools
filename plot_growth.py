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

def parse_date(date_str):
    """
    Parses date string from EXIF (YYYY:MM:DD HH:MM:SS) or other formats.
    Returns a datetime object or None.
    """
    formats = [
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def main():
    parser = argparse.ArgumentParser(description="Generate a chart of picture collection growth over time.")
    parser.add_argument("directory", help="Path to the directory containing .collection.db")
    parser.add_argument("--group-by", choices=["month", "year"], default="month", help="Group pictures by 'month' or 'year'")
    args = parser.parse_args()

    target_dir = os.path.abspath(args.directory)
    db_path = os.path.join(target_dir, ".collection.db")

    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query data
        cursor.execute("SELECT date_taken, file_size FROM pictures WHERE date_taken IS NOT NULL")
        rows = cursor.fetchall()
        
        if not rows:
            print("No pictures with date information found in the database.")
            conn.close()
            return

        # Process data
        growth_data = {}
        
        for date_str, size in rows:
            dt = parse_date(date_str)
            if dt:
                if args.group_by == "year":
                    key = dt.strftime("%Y")
                else:
                    key = dt.strftime("%Y-%m")
                growth_data[key] = growth_data.get(key, 0) + size
        
        if not growth_data:
            print("Could not parse any dates.")
            conn.close()
            return

        # Sort by key (month or year)
        sorted_keys = sorted(growth_data.keys())
        
        # Calculate cumulative size
        cumulative_sizes = []
        current_total = 0
        for key in sorted_keys:
            current_total += growth_data[key]
            cumulative_sizes.append(current_total)
            
        # Convert bytes to MB for better readability
        cumulative_sizes_mb = [size / (1024 * 1024) for size in cumulative_sizes]

        # Calculate periodic sizes in MB
        periodic_sizes_mb = [growth_data[key] / (1024 * 1024) for key in sorted_keys]

        # Plotting
        try:
            import matplotlib.pyplot as plt

            label = "Year" if args.group_by == "year" else "Month"

            # Chart 1: Cumulative Growth
            plt.figure(figsize=(12, 6))
            plt.bar(sorted_keys, cumulative_sizes_mb, color='skyblue')
            
            plt.xlabel(label)
            plt.ylabel("Collection Size (MB)")
            plt.title("Picture Collection Growth Over Time")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            output_path = os.path.join(target_dir, "collection_growth.png")
            plt.savefig(output_path)
            print(f"Chart saved to: {output_path}")

            # Chart 2: Periodic Size
            plt.figure(figsize=(12, 6))
            plt.bar(sorted_keys, periodic_sizes_mb, color='lightgreen')

            plt.xlabel(label)
            plt.ylabel(f"{label}ly Size (MB)")
            plt.title(f"{label}ly Picture Collection Size")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            output_path_periodic = os.path.join(target_dir, "collection_monthly_size.png")
            plt.savefig(output_path_periodic)
            print(f"Chart saved to: {output_path_periodic}")

        except ImportError:
            print("matplotlib not installed. Skipping chart generation.")
            print("Data that would be plotted (Cumulative):")
            for key, size in zip(sorted_keys, cumulative_sizes_mb):
                print(f"{key}: {size:.2f} MB")

            print(f"\nData that would be plotted ({'Yearly' if args.group_by == 'year' else 'Monthly'}):")
            for key, size in zip(sorted_keys, periodic_sizes_mb):
                print(f"{key}: {size:.2f} MB")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
