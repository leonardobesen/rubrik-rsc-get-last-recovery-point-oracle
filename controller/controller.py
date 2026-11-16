import argparse
import csv
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import configuration.configuration as conf
from data import data_parser
from model.protected_object import ProtectedObject

logger = logging.getLogger(__name__)


def parse_command_line_args():
    """Parse command-line arguments for the Oracle-host recovery-point workflow."""
    parser = argparse.ArgumentParser(
        description="Query Rubrik RSC for Oracle database and DG recovery points by hostname.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input hostname_list.csv
        """
    )

    parser.add_argument(
        "--input",
        help="CSV filename to use from the reports/input/ folder",
        required=False,
    )

    return parser.parse_args()


def _prompt_file_selection(csv_files: list[Path]) -> Path:
    """Prompt the user to select a CSV file when no file is supplied."""
    if len(csv_files) == 1:
        print(f"Using: {csv_files[0].name}")
        return csv_files[0]

    print("\nAvailable CSV files:")
    print(f"{'#':<3} {'Filename':<40} {'Size':<12} {'Modified':<20}")
    print("-" * 75)

    for idx, path in enumerate(csv_files, start=1):
        size = path.stat().st_size
        mod_time = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_str = f"{size:,} B" if size < 1024 else f"{size/1024:.1f} KB"
        print(f"{idx:<3} {path.name:<40} {size_str:<12} {mod_time:<20}")

    print("-" * 75)
    try:
        selection = int(input("Select a CSV file (enter number): ")) - 1
    except ValueError:
        print("Invalid input. Please enter a number.")
        sys.exit(1)

    if selection not in range(len(csv_files)):
        print("Invalid selection.")
        sys.exit(1)

    return csv_files[selection]


def _normalize_hostname_values(raw_value: str | None) -> list[str]:
    if raw_value is None:
        return []

    cleaned = raw_value.strip().strip('"').strip("'")
    if not cleaned:
        return []

    values = [item.strip().strip('"').strip("'") for item in cleaned.split(",")]
    return [value for value in values if value and value.lower() != "nan"]


def _read_hostnames_from_file(csv_file: Path) -> list[str]:
    try:
        with csv_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = [name.strip().lower() for name in (reader.fieldnames or [])]

            if reader.fieldnames and "location" in fieldnames:
                values: list[str] = []
                seen: set[str] = set()
                for row in reader:
                    for hostname in _normalize_hostname_values(row.get("Location") or row.get("location")):
                        if hostname and hostname not in seen:
                            seen.add(hostname)
                            values.append(hostname)
                return values

            # Fallback for simple host lists without a Rubrik export header.
            handle.seek(0)
            values: list[str] = []
            seen: set[str] = set()
            for row in csv.reader(handle):
                for cell in row:
                    for hostname in _normalize_hostname_values(cell):
                        if hostname and hostname not in seen:
                            seen.add(hostname)
                            values.append(hostname)
            return values
    except Exception as e:
        print(f"Failed to read CSV file: {e}")
        sys.exit(1)

    return []


def parse_csv_files(csv_filename: str | None = None) -> list[str]:
    """Read hostnames from a CSV file in reports/input."""
    directory = Path(conf.report_input_path())

    if not directory.is_dir():
        print(f"Directory does not exist: {directory}")
        sys.exit(1)

    csv_files = sorted(directory.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in: {directory}")
        sys.exit(1)

    if csv_filename:
        matching_file = next((f for f in csv_files if f.name == csv_filename), None)
        if matching_file:
            print(f"Using specified file: {matching_file.name}")
            selected_file = matching_file
        else:
            print(f"Error: CSV file '{csv_filename}' not found in {directory}")
            print(f"Available files: {', '.join(f.name for f in csv_files)}")
            sys.exit(1)
    else:
        selected_file = _prompt_file_selection(csv_files)

    print(f"Selected: {selected_file}")
    return _read_hostnames_from_file(selected_file)


def get_oracle_objects_for_hosts(
    access_token: str,
    hostnames: list[str],
    selected_clusters: list[str] | None = None,
) -> list[ProtectedObject]:
    return data_parser.get_oracle_protected_objects(
        access_token=access_token,
        hostnames=hostnames,
        selected_clusters=selected_clusters or [],
    )


def get_oracle_recovery_points(
    access_token: str,
    hostnames: list[str],
    selected_clusters: list[str] | None = None,
) -> list[dict]:
    oracle_objects = get_oracle_objects_for_hosts(
        access_token=access_token,
        hostnames=hostnames,
        selected_clusters=selected_clusters,
    )

    recovery_points: list[dict] = []
    for workload in oracle_objects:
        recovery_points.extend(
            data_parser.get_latest_recovery_points_for_workload(access_token, workload)
        )

    return recovery_points

