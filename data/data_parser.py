import logging

from tqdm import tqdm

import graphql.queries
from connection.wrapper import request
from data import data_operation
from model.cluster import Cluster
from model.protected_object import ProtectedObject

logger = logging.getLogger(__name__)


def get_all_cluster_info(access_token: str) -> list[Cluster]:
    """Fetch all clusters information."""
    clusters = []

    try:
        query, variables = graphql.queries.all_cluster_info_query()
        response = request(access_token, query, variables)
        nodes = response.get("data", {}).get("allClusterConnection", {}).get("nodes", [])
    except Exception as exc:
        logger.exception("Failed to fetch cluster data")
        raise LookupError("Unable to collect clusters data!") from exc

    if not nodes:
        return []

    for item in nodes:
        cluster = data_operation.create_cluster_from_data(item)
        if cluster:
            clusters.append(cluster)

    return clusters


def get_oracle_protected_objects(
    access_token: str,
    hostnames: list[str],
    selected_clusters: list[str] | None = None,
) -> list[ProtectedObject]:
    """Query Rubrik RSC for Oracle database and DG workloads that match the provided hostnames."""
    protected_objects: list[ProtectedObject] = []
    selected_clusters = selected_clusters or []

    for hostname in tqdm(hostnames, desc="Searching Oracle hosts"):
        try:
            query, variables = graphql.queries.search_oracle_object_by_hostname(
                hostname=hostname,
                cluster_ids=selected_clusters,
            )
            response = request(access_token, query, variables)
            nodes = response.get("data", {}).get("globalSearchResults", {}).get("nodes", [])
        except Exception:
            logger.warning("Failed to fetch Oracle object data for host %s", hostname)
            continue

        if not nodes:
            logger.warning("No Oracle DB or DG objects found for hostname: %s", hostname)
            continue

        matched = 0
        for item in nodes:
            object_type = item.get("objectType")
            if object_type not in {"OracleDatabase", "ORACLE_DATA_GUARD_GROUP"}:
                continue

            protected_object = data_operation.create_object_from_data(item)
            if protected_object is None:
                continue

            protected_object.search_term = hostname
            protected_objects.append(protected_object)
            matched += 1

        if matched == 0:
            logger.warning(
                "No Oracle Database or Oracle DG workloads found for hostname %s in current search results.",
                hostname,
            )

    return protected_objects


def get_latest_recovery_points_for_workload(
    access_token: str,
    workload: ProtectedObject,
) -> list[dict]:
    """Fetch the latest recoverable range for each tablespace for a given Oracle workload ID."""
    try:
        query, variables = graphql.queries.get_latest_recoverable_date(workload.id)
        response = request(access_token, query, variables)
        ranges = response.get("data", {}).get("oracleRecoverableRanges", {}).get("data", [])
    except Exception:
        logger.warning("Failed to fetch recoverable range data for workload %s (%s)", workload.name, workload.id)
        return []

    if not ranges:
        logger.warning(
            "No recoverable ranges returned for workload %s (%s). This workload will be skipped.",
            workload.name,
            workload.id,
        )
        return []

    latest_points = data_operation.extract_latest_tablespace_recovery_points(ranges)
    if not latest_points:
        logger.warning(
            "No tablespace recoverable points were extracted for workload %s (%s).",
            workload.name,
            workload.id,
        )
        return []

    for point in latest_points:
        point["objectId"] = workload.id
        point["objectName"] = workload.name
        point["objectType"] = workload.object_type

    return latest_points
