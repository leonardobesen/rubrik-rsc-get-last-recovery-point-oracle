# Oracle Recovery Point Reporter

This utility searches Rubrik RSC for Oracle database and Oracle Data Guard objects by hostname, reads the latest recoverable ranges for each workload, and exports the newest relevant tablespace recovery point for each Oracle host/database combination.

## What it does

- Reads a list of hostnames from a CSV file located in the reports/input folder.
- Queries Rubrik RSC for Oracle Database and Oracle Data Guard Group objects that match those hostnames.
- Calls the Oracle recoverable-range query for each matching workload.
- Walks the returned ranges from newest to oldest and keeps the newest end time for each tablespace.
- Saves the final result to a CSV report in the reports folder.
- Logs missing hosts, missing workloads, and missing recoverable ranges to a file in the logs folder instead of stopping the workflow.

## Requirements

- Python 3.10+
- Network access to the Rubrik RSC tenant
- Service account configuration in configuration/config.json

## Installation

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration

Create or update configuration/config.json with your Rubrik RSC tenant values:

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "name": "service_account_name",
  "access_token_uri": "https://yourdomain.my.rubrik.com/api/client_token",
  "graphql_url": "https://yourdomain.my.rubrik.com/api/graphql"
}
```

## Input file

Place one CSV file in the reports/input folder. The file may contain one hostname per line or comma-separated values.

Example:

```csv
oracle-host-01
oracle-host-02
oracle-host-03
```

## Run

```bash
python main.py --input hostname_list.csv
```

If no file is passed, the script prompts you to choose one from the reports/input folder.

## Output

The script writes a CSV named like:

```text
reports/Oracle_Recovery_Points_21-11-2026_14_30_00.csv
```

Columns:

- hostOrRacName
- databaseName
- tablespace
- latest_end_time

## Logging

The project writes runtime warnings and informational messages to the logs folder:

```text
logs/oracle_recovery.log
```

If a hostname is not found, a workload has no recoverable ranges, or no tablespace data is extracted, the run continues and the issue is logged instead of aborting the process.

## Troubleshooting

- Verify the service account has access to the Oracle workloads in RSC.
- Confirm the hostname CSV contains the exact host names used by Rubrik.
- Review logs/oracle_recovery.log for skipped records and query failures.
