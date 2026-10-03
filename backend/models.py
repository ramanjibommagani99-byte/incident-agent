from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class IncidentStatus(str, Enum):
    NEW = "New"
    TRIAGED = "Triaged"
    INVESTIGATING = "Investigating"
    AWAITING_APPROVAL = "Awaiting Approval"
    MITIGATED = "Mitigated"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class Risk(str, Enum):
    SAFE = "safe"
    SENSITIVE = "sensitive"


class ActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class Incident(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    title: str
    description: str = ""
    source: str = "manual"
    service: str | None = None
    category: str = "Unknown"
    severity: str = "SEV3"
    priority: int = 3
    status: IncidentStatus = IncidentStatus.NEW
    assignee: str | None = None
    confidence: float = 0.0
    ai_summary: str = ""
    probable_root_cause: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None


class LogEntry(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    timestamp: datetime = Field(default_factory=utcnow, index=True)
    service: str = Field(index=True)
    level: str = Field(default="INFO", index=True)
    message: str
    template_id: str | None = None
    trace_id: str | None = Field(default=None, index=True)
    incident_id: str | None = Field(default=None, foreign_key="incident.id", index=True)


class TimelineEvent(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    incident_id: str = Field(foreign_key="incident.id", index=True)
    timestamp: datetime = Field(default_factory=utcnow)
    actor: str = "system"
    type: str
    detail: str
    evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class ProposedAction(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    incident_id: str = Field(foreign_key="incident.id", index=True)
    description: str
    risk: Risk
    status: ActionStatus = ActionStatus.PENDING
    decided_by: str | None = None
    decided_at: datetime | None = None


class AuditLog(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    sequence: int | None = Field(default=None, primary_key=False, index=True)
    timestamp: datetime = Field(default_factory=utcnow)
    actor: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    prev_hash: str = "0" * 64
    hash: str


class KBArticle(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    title: str
    category: str
    content_md: str
    source_incident_id: str | None = None
