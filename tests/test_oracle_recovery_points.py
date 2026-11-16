import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from controller import controller
from data.data_operation import extract_latest_tablespace_recovery_points
from file_manager.write_to_file import _normalize_output_datetime


class ExtractLatestTablespaceRecoveryPointsTest(unittest.TestCase):
    def test_extract_latest_tablespace_recovery_points_uses_latest_range_per_tablespace(self):
        ranges = [
            {
                "beginTime": "2024-01-01T00:00:00Z",
                "endTime": "2024-01-02T00:00:00Z",
                "dbSnapshotSummaries": [
                    {
                        "databaseName": "db1",
                        "hostOrRacName": "hostA",
                        "tablespaces": ["ts1", "ts2"],
                    }
                ],
            },
            {
                "beginTime": "2024-01-03T00:00:00Z",
                "endTime": "2024-01-04T00:00:00Z",
                "dbSnapshotSummaries": [
                    {
                        "databaseName": "db1",
                        "hostOrRacName": "hostA",
                        "tablespaces": ["ts2"],
                    }
                ],
            },
            {
                "beginTime": "2024-01-05T00:00:00Z",
                "endTime": "2024-01-06T00:00:00Z",
                "dbSnapshotSummaries": [
                    {
                        "databaseName": "db1",
                        "hostOrRacName": "hostA",
                        "tablespaces": ["ts1"],
                    }
                ],
            },
            {
                "beginTime": "2024-01-07T00:00:00Z",
                "endTime": "2024-01-08T00:00:00Z",
                "dbSnapshotSummaries": [
                    {
                        "databaseName": "db1",
                        "hostOrRacName": "hostA",
                        "tablespaces": ["ts1", "ts3"],
                    }
                ],
            },
        ]

        actual = extract_latest_tablespace_recovery_points(ranges)

        self.assertEqual(
            actual,
            [
                {
                    "hostOrRacName": "hostA",
                    "databaseName": "db1",
                    "tablespace": "ts1",
                    "latest_end_time": datetime.fromisoformat("2024-01-08T00:00:00+00:00"),
                },
                {
                    "hostOrRacName": "hostA",
                    "databaseName": "db1",
                    "tablespace": "ts2",
                    "latest_end_time": datetime.fromisoformat("2024-01-04T00:00:00+00:00"),
                },
                {
                    "hostOrRacName": "hostA",
                    "databaseName": "db1",
                    "tablespace": "ts3",
                    "latest_end_time": datetime.fromisoformat("2024-01-08T00:00:00+00:00"),
                },
            ],
        )

    def test_parse_hostnames_from_rubrik_report_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "rubrik_export.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Cluster", "Location", "Object", "Object State", "Last Successful Backup"])
                writer.writerow(["bkp-pd-0003", "orcl-c4ovmw-225496-p-2123-ce", "C4OVMWPP", "Active", "11/16/2026 12:23:09 PM"])
                writer.writerow(["bkp-pd-0003", "", "CLIPPIPP", "Active", "11/16/2026 11:41:23 AM"])
                writer.writerow(["bkp-pd-0012", "orcl-shared-tmp-6298-p-c-tesp7, orcl-dg-shared-tmp-6298-p-c-tesp7", "TMODA", "Active", "11/16/2026 10:47:42 AM"])

            parsed = controller._read_hostnames_from_file(csv_path)

        self.assertEqual(
            parsed,
            [
                "orcl-c4ovmw-225496-p-2123-ce",
                "orcl-shared-tmp-6298-p-c-tesp7",
                "orcl-dg-shared-tmp-6298-p-c-tesp7",
            ],
        )

    def test_normalize_output_datetime_uses_brazil_timezone(self):
        self.assertEqual(
            _normalize_output_datetime("2024-01-08T00:00:00+00:00"),
            "2024-01-07T21:00:00-03:00",
        )


if __name__ == "__main__":
    unittest.main()
