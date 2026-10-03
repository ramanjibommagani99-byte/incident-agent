from sqlmodel import Session

from .audit import append_audit
from .models import Incident, IncidentStatus, TimelineEvent, utcnow


TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.NEW: {IncidentStatus.TRIAGED},
    IncidentStatus.TRIAGED: {IncidentStatus.INVESTIGATING},
    IncidentStatus.INVESTIGATING: {IncidentStatus.AWAITING_APPROVAL, IncidentStatus.RESOLVED},
    IncidentStatus.AWAITING_APPROVAL: {IncidentStatus.MITIGATED, IncidentStatus.INVESTIGATING},
    IncidentStatus.MITIGATED: {IncidentStatus.RESOLVED},
    IncidentStatus.RESOLVED: {IncidentStatus.CLOSED},
    IncidentStatus.CLOSED: set(),
}


def transition(session: Session, incident: Incident, target: IncidentStatus, actor: str = "system") -> Incident:
    if target not in TRANSITIONS[incident.status]:
        raise ValueError(f"Invalid incident transition: {incident.status.value} -> {target.value}")
    previous = incident.status
    incident.status = target
    if target == IncidentStatus.RESOLVED:
        incident.resolved_at = utcnow()
    session.add(incident)
    detail = f"Status changed from {previous.value} to {target.value}"
    session.add(TimelineEvent(incident_id=incident.id, actor=actor, type="status_change", detail=detail))
    append_audit(session, actor, "incident.status_changed", {"incident_id": incident.id, "from": previous.value, "to": target.value})
    return incident
