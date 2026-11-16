from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProtectedObject:
    id: str
    name: str
    object_type: str
    sla_id: str | None = None
    sla_name: str | None = None
    search_term: str | None = None
    location: str | None = None

    def __str__(self):
        return f"Object(id={self.id}, name={self.name}, type={self.object_type})"


@dataclass
class OracleRecoveryPoint:
    host_or_rac_name: str
    database_name: str
    tablespace: str
    latest_end_time: datetime
    object_id: str | None = None
    object_name: str | None = None
    object_type: str | None = None
