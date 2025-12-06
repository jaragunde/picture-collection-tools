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
    parser.add_argument("--date-before", help="Filter pictures taken before this date (YYYY-MM-DD)")
    parser.add_argument("--date-after", help="Filter pictures taken after this date (YYYY-MM-DD)")
    parser.add_argument("--group-dirs", action="store_true", help="Group pictures by directory (stacked bar chart)")
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
        cursor.execute("SELECT date_taken, file_size, file_path FROM pictures WHERE date_taken IS NOT NULL")
        rows = cursor.fetchall()
        
        if not rows:
            print("No pictures with date information found in the database.")
            conn.close()
            return

        # Process data
        # Structure: growth_data[time_key][directory] = size
        growth_data = {}
        all_directories = set()
        
        date_before_dt = None
        if args.date_before:
            try:
                date_before_dt = datetime.strptime(args.date_before, "%Y-%m-%d")
            except ValueError:
                print(f"Error: Invalid date format for --date-before: {args.date_before}. Use YYYY-MM-DD.")
                conn.close()
                sys.exit(1)

        date_after_dt = None
        if args.date_after:
            try:
                date_after_dt = datetime.strptime(args.date_after, "%Y-%m-%d")
            except ValueError:
                print(f"Error: Invalid date format for --date-after: {args.date_after}. Use YYYY-MM-DD.")
                conn.close()
                sys.exit(1)

        for date_str, size, file_path in rows:
            dt = parse_date(date_str)
            if dt:
                if date_before_dt and dt >= date_before_dt:
                    continue
                if date_after_dt and dt <= date_after_dt:
                    continue

                if args.group_by == "year":
                    key = dt.strftime("%Y")
                else:
                    key = dt.strftime("%Y-%m")

                if args.group_dirs:
                    # Get directory name relative to target_dir
                    try:
                        rel_dir = os.path.relpath(os.path.dirname(file_path), target_dir)
                        if rel_dir == ".":
                            directory = "Root"
                        else:
                            directory = rel_dir
                    except ValueError:
                        # Fallback if paths are on different drives or something
                        directory = os.path.basename(os.path.dirname(file_path))
                else:
                    directory = "Total"

                if key not in growth_data:
                    growth_data[key] = {}

                growth_data[key][directory] = growth_data[key].get(directory, 0) + size
                all_directories.add(directory)

        if not growth_data:
            print("Could not parse any dates or no data after filtering.")
            conn.close()
            return

        # Sort by key (month or year)
        sorted_keys = sorted(growth_data.keys())
        sorted_directories = sorted(list(all_directories))

        # Prepare data for plotting
        # We need a list of sizes for each directory, aligned with sorted_keys

        # For periodic (monthly/yearly) chart:
        periodic_data = {d: [] for d in sorted_directories}
        for key in sorted_keys:
            for d in sorted_directories:
                size = growth_data[key].get(d, 0)
                periodic_data[d].append(size / (1024 * 1024)) # MB

        # For cumulative chart:
        # We need to accumulate sizes per directory over time
        cumulative_data = {d: [] for d in sorted_directories}
        current_totals = {d: 0 for d in sorted_directories}

        for key in sorted_keys:
            for d in sorted_directories:
                size = growth_data[key].get(d, 0)
                current_totals[d] += size
                cumulative_data[d].append(current_totals[d] / (1024 * 1024)) # MB

        # Plotting
        try:
            import matplotlib.pyplot as plt
            import numpy as np

            label = "Year" if args.group_by == "year" else "Month"

            # Helper to plot stacked bars
            def plot_chart(data_dict, title, ylabel, filename):
                plt.figure(figsize=(12, 6))

                bottom = np.zeros(len(sorted_keys))

                if args.group_dirs:
                    for d in sorted_directories:
                        values = data_dict[d]
                        plt.bar(sorted_keys, values, bottom=bottom, label=d)
                        bottom += np.array(values)
                    plt.legend(title="Directory", bbox_to_anchor=(1.05, 1), loc='upper left')
                else:
                    # Single series (Total)
                    values = data_dict["Total"]
                    plt.bar(sorted_keys, values, color='skyblue' if 'Growth' in title else 'lightgreen')

                plt.xlabel(label)
                plt.ylabel(ylabel)
                plt.title(title)
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()

                output_path = os.path.join(target_dir, filename)
                plt.savefig(output_path)
                print(f"Chart saved to: {output_path}")

            # Chart 1: Cumulative Growth
            plot_chart(cumulative_data, "Picture Collection Growth Over Time", "Collection Size (MB)", "collection_growth.png")

            # Chart 2: Periodic Size
            plot_chart(periodic_data, f"{label}ly Picture Collection Size", f"{label}ly Size (MB)", "collection_monthly_size.png")

        except ImportError:
            print("matplotlib not installed. Skipping chart generation.")
            # Fallback print - simplified to just totals for now to avoid spamming too much
            print("Data that would be plotted (Cumulative Totals):")
            for i, key in enumerate(sorted_keys):
                total = sum(cumulative_data[d][i] for d in sorted_directories)
                print(f"{key}: {total:.2f} MB")

            print(f"\nData that would be plotted ({'Yearly' if args.group_by == 'year' else 'Monthly'} Totals):")
            for i, key in enumerate(sorted_keys):
                total = sum(periodic_data[d][i] for d in sorted_directories)
                print(f"{key}: {total:.2f} MB")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
