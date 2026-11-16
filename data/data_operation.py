import logging
from datetime import datetime
from typing import Any

from model.cluster import Cluster
from model.protected_object import ProtectedObject

logger = logging.getLogger(__name__)


def create_cluster_from_data(data: dict) -> Cluster | None:
    """Create a Cluster object from dictionary data."""
    try:
        return Cluster(
            id=data["id"],
            name=data["name"],
            connected_state=data.get("state", {}).get("connectedState"),
        )
    except KeyError as e:
        logger.error(f"Missing expected cluster data field: {e}", exc_info=True)
    except Exception as e:
        logger.exception("Unexpected error while creating Cluster object", exc_info=True)
    return None


def create_object_from_data(data: dict) -> ProtectedObject | None:
    """Create a protected-object model from GraphQL search results."""
    try:
        protect_obj = ProtectedObject(
            id=data["id"],
            name=data["name"],
            object_type=data["objectType"],
            sla_id=data.get("effectiveSlaDomain", {}).get("id", ""),
            sla_name=data.get("effectiveSlaDomain", {}).get("name", "")
        )
        protect_obj.location = data.get("hostAddress", "")
        return protect_obj
    except KeyError as e:
        logger.error(f"Missing expected object data field: {e}", exc_info=True)
    except Exception as e:
        logger.exception("Unexpected error while creating ProtectedObject", exc_info=True)
    return None


def _parse_iso_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        logger.warning("Unable to parse datetime value: %s", value)
        return None


def extract_latest_tablespace_recovery_points(recoverable_ranges: list[dict]) -> list[dict]:
    """Return the newest recoverable end time for each host/database/tablespace in the ranges list.

    The GraphQL result is sorted ascending by range start/end time. We walk the list from newest to oldest,
    keeping the first time each host/database/tablespace is seen so the newest relevant recovery point is kept.
    """
    latest_by_key: dict[tuple[str, str, str], dict] = {}

    for recoverable_range in reversed(recoverable_ranges or []):
        end_time = _parse_iso_datetime(recoverable_range.get("endTime"))
        if end_time is None:
            continue

        for summary in recoverable_range.get("dbSnapshotSummaries") or []:
            host_name = summary.get("hostOrRacName") or ""
            database_name = summary.get("databaseName") or ""
            tablespaces = summary.get("tablespaces") or []

            if isinstance(tablespaces, str):
                tablespaces = [item.strip() for item in tablespaces.split(",") if item.strip()]

            for tablespace in tablespaces:
                if not tablespace:
                    continue

                key = (host_name, database_name, tablespace)
                if key not in latest_by_key:
                    latest_by_key[key] = {
                        "hostOrRacName": host_name,
                        "databaseName": database_name,
                        "tablespace": tablespace,
                        "latest_end_time": end_time,
                    }

    ordered_rows = sorted(
        latest_by_key.values(),
        key=lambda row: (
            str(row["hostOrRacName"]),
            str(row["databaseName"]),
            str(row["tablespace"]),
        )
    )

    return ordered_rows
