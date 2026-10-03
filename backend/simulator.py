from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session

from .models import Incident, IncidentStatus, LogEntry, ProposedAction, Risk, TimelineEvent, utcnow
from .workflow import transition


def inject_bad_deploy(session: Session) -> Incident:
    """Create a deterministic checkout outage and its simulated evidence."""
    incident = Incident(
        title="Checkout failures after deploy v2.4.1",
        description="A bad checkout-service deploy is followed by a 5xx spike and database connection pool exhaustion.",
        source="simulator",
        service="checkout-service",
    )
    session.add(incident)
    session.flush()
    now = utcnow()
    logs = [
        LogEntry(timestamp=now - timedelta(minutes=4), service="checkout-service", level="INFO", message="deployment completed version=v2.4.1", trace_id="trace-demo-01", incident_id=incident.id),
        LogEntry(timestamp=now - timedelta(minutes=3), service="checkout-service", level="ERROR", message="HTTP 503 while creating checkout session", trace_id="trace-demo-02", incident_id=incident.id),
        LogEntry(timestamp=now - timedelta(minutes=3), service="orders-service", level="ERROR", message="upstream checkout request failed status=503", trace_id="trace-demo-02", incident_id=incident.id),
        LogEntry(timestamp=now - timedelta(minutes=2), service="checkout-service", level="ERROR", message="database connection pool exhausted active=100 max=100", trace_id="trace-demo-03", incident_id=incident.id),
        LogEntry(timestamp=now - timedelta(minutes=1), service="payments-service", level="WARN", message="retry queue growing after checkout timeout", trace_id="trace-demo-03", incident_id=incident.id),
    ]
    session.add_all(logs)
    session.flush()
    session.add(TimelineEvent(incident_id=incident.id, actor="simulator", type="failure_injected", detail="Injected checkout-service v2.4.1 failure with correlated logs."))
    transition(session, incident, IncidentStatus.TRIAGED)
    transition(session, incident, IncidentStatus.INVESTIGATING)
    incident.category = "Availability"
    incident.severity = "SEV1"
    incident.priority = 1
    incident.confidence = 0.87
    incident.ai_summary = "Checkout 5xx errors began after v2.4.1 deployment and correlate with database pool exhaustion across three services."
    incident.probable_root_cause = "Checkout-service v2.4.1 appears to exhaust the database connection pool, causing upstream 503s and downstream retries."
    session.add(incident)
    action = ProposedAction(incident_id=incident.id, description="Rollback checkout-service from v2.4.1 to v2.4.0", risk=Risk.SENSITIVE)
    session.add(action)
    session.add(TimelineEvent(incident_id=incident.id, actor="ai", type="analysis", detail=incident.ai_summary, evidence_ids=[row.id for row in logs]))
    transition(session, incident, IncidentStatus.AWAITING_APPROVAL, actor="ai")
    return incident
