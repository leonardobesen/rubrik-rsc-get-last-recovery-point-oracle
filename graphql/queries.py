from configuration.configuration import get_excluded_clusters_uuids


def all_cluster_info_query() -> tuple[str, dict]:
    variables = {
        "filter": {
            "productFilters": [
                {
                    "productType": "CDM"
                }
            ],
            "excludeId": get_excluded_clusters_uuids()
        }
    }

    query = f"""query ListAllClustersInfo($filter: ClusterFilterInput,$sortBy: ClusterSortByEnum = ClusterName){{
      allClusterConnection(filter: $filter, sortBy: $sortBy){{
        nodes{{
          id
          name
          state{{
            connectedState
          }}
        }}
      }}
    }}"""

    return query, variables


def search_object(name: str, cluster_ids: list[str], is_relic: bool = False, is_nas_share_stale: bool = False) -> tuple[str, dict]:
    variables = {
        "filter": [
            {
                "field": "LOCATION",
                "texts": [
                    name
                ]
            },
            {
                "field": "IS_GHOST",
                "texts": [
                    "false"
                ]
            },
            {
                "field": "IS_ACTIVE",
                "texts": [
                    "true"
                ]
            }
        ],
        "sortBy": "NAME",
        "sortOrder": "ASC",
        "first": 300
    }

    if cluster_ids:
        variables["filter"].append({
            "field": "CLUSTER_ID",
            "texts": cluster_ids
        })

    if is_relic:
        variables["filter"].append({
            "field": "IS_RELIC",
            "texts": [
                "true"
            ]
        })

    if is_nas_share_stale == True:
        variables["filter"].append({
            "field": "IS_STALE",
            "texts": [
                "true"
            ]
        })

    query = """query GlobalSearchLocationQuery(
      $first: Int!,
      $filter: [Filter!]!, 
      $sortBy: HierarchySortByField, 
      $sortOrder: SortOrder,) {
      globalSearchResults(
        first: $first
        filter: $filter
        sortBy: $sortBy
        sortOrder: $sortOrder
      ) {
        nodes {
          id
          name
          objectType
          ...on NasShare {
            hostAddress
          }
          effectiveSlaDomain {
            id
            name
          }
        }
      }
    }
    """

    return query, variables


def search_oracle_object_by_hostname(hostname: str, cluster_ids: list[str] | None = None) -> tuple[str, dict]:
    """Search Rubrik RSC for Oracle database and DG objects related to a hostname."""
    variables = {
        "filter": [
            {"field": "LOCATION", "texts": [hostname]},
            {"field": "IS_GHOST", "texts": ["false"]},
            {"field": "IS_ACTIVE", "texts": ["true"]},
        ],
        "sortBy": "NAME",
        "sortOrder": "ASC",
        "first": 300,
    }

    if cluster_ids:
        variables["filter"].append({"field": "CLUSTER_ID", "texts": cluster_ids})

    query = """query OracleHostObjectSearch(
      $first: Int!,
      $filter: [Filter!]!,
      $sortBy: HierarchySortByField,
      $sortOrder: SortOrder
    ) {
      globalSearchResults(
        first: $first
        filter: $filter
        sortBy: $sortBy
        sortOrder: $sortOrder
      ) {
        nodes {
          id
          name
          objectType
          effectiveSlaDomain {
            id
            name
          }
        }
      }
    }"""

    return query, variables


def take_on_demand_snapshot_mutation(sla_id: str, workload_ids: list[str]) -> tuple[str, dict]:
    """GraphQL mutation to trigger on-demand snapshots for multiple objects within the same SLA"""
    variables = {
        "input": {
            "slaId": sla_id,
            "workloadIds": workload_ids
        }
    }

    mutation = """mutation massOnDemandOracle($input: TakeOnDemandSnapshotInput!){
      takeOnDemandSnapshot(input: $input) {
        taskchainUuids {
          objectId: workloadId
          taskchainUuid
        }
        errors {
          objectId: workloadId
          error
        }
      }
    }"""

    return mutation, variables

def get_latest_recoverable_date(workload_id: str) -> tuple[str, dict]:
    """GraphQL query to get the latest recoverable date for a given workload"""
    variables = {
  "input": {
    "id": workload_id,
    "shouldIncludeDbSnapshotSummaries": True
  }
}

    query = """query DataRecuperaveisOracle($input: GetOracleDbRecoverableRangesInput!) {
  oracleRecoverableRanges(input: $input) {
    data {
      beginTime
      endTime
      dbSnapshotSummaries {
        databaseName
        hostOrRacName
        tablespaces 
      }
    }
  }
}"""

    return query, variables