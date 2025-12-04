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
        monthly_growth = {}
        
        for date_str, size in rows:
            dt = parse_date(date_str)
            if dt:
                month_key = dt.strftime("%Y-%m")
                monthly_growth[month_key] = monthly_growth.get(month_key, 0) + size
        
        if not monthly_growth:
            print("Could not parse any dates.")
            conn.close()
            return

        # Sort by month
        sorted_months = sorted(monthly_growth.keys())
        
        # Calculate cumulative size
        cumulative_sizes = []
        current_total = 0
        for month in sorted_months:
            current_total += monthly_growth[month]
            cumulative_sizes.append(current_total)
            
        # Convert bytes to MB for better readability
        cumulative_sizes_mb = [size / (1024 * 1024) for size in cumulative_sizes]

        # Calculate monthly sizes in MB
        monthly_sizes_mb = [monthly_growth[month] / (1024 * 1024) for month in sorted_months]

        # Plotting
        try:
            import matplotlib.pyplot as plt
            
            # Chart 1: Cumulative Growth
            plt.figure(figsize=(12, 6))
            plt.bar(sorted_months, cumulative_sizes_mb, color='skyblue')
            
            plt.xlabel("Month")
            plt.ylabel("Collection Size (MB)")
            plt.title("Picture Collection Growth Over Time")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            output_path = os.path.join(target_dir, "collection_growth.png")
            plt.savefig(output_path)
            print(f"Chart saved to: {output_path}")

            # Chart 2: Monthly Size
            plt.figure(figsize=(12, 6))
            plt.bar(sorted_months, monthly_sizes_mb, color='lightgreen')

            plt.xlabel("Month")
            plt.ylabel("Monthly Size (MB)")
            plt.title("Monthly Picture Collection Size")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            output_path_monthly = os.path.join(target_dir, "collection_monthly_size.png")
            plt.savefig(output_path_monthly)
            print(f"Chart saved to: {output_path_monthly}")

        except ImportError:
            print("matplotlib not installed. Skipping chart generation.")
            print("Data that would be plotted (Cumulative):")
            for month, size in zip(sorted_months, cumulative_sizes_mb):
                print(f"{month}: {size:.2f} MB")

            print("\nData that would be plotted (Monthly):")
            for month, size in zip(sorted_months, monthly_sizes_mb):
                print(f"{month}: {size:.2f} MB")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
