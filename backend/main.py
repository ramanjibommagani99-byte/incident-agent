from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from .audit import append_audit, verify_chain
from .database import get_session, init_db
from .models import ActionStatus, AuditLog, Incident, IncidentStatus, KBArticle, LogEntry, ProposedAction, Risk, TimelineEvent, utcnow
from .pipeline.analyze import analyze_incident
from .simulator import inject_bad_deploy
from .workflow import transition

app = FastAPI(title="PS-61 Incident Response Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IncidentCreate(BaseModel):
    title: str
    description: str = ""
    source: str = "manual"
    service: str | None = None


class LogInput(BaseModel):
    timestamp: datetime | None = None
    service: str
    level: str = "INFO"
    message: str
    trace_id: str | None = None


class LogBatch(BaseModel):
    logs: list[LogInput]


class AlertInput(BaseModel):
    title: str
    description: str = ""
    service: str | None = None
    severity: str | None = None
    timestamp: datetime | None = None


class Decision(BaseModel):
    decided_by: str = Field(min_length=1)


class IncidentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    source: str | None = None
    service: str | None = None
    status: IncidentStatus | None = None
    assignee: str | None = None

    


class ActionCreate(BaseModel):
    description: str = Field(min_length=1)
    risk: Risk


def serialize(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


def incident_detail(session: Session, incident: Incident) -> dict[str, Any]:
    logs = session.exec(select(LogEntry).where(LogEntry.incident_id == incident.id).order_by(LogEntry.timestamp)).all()
    events = session.exec(select(TimelineEvent).where(TimelineEvent.incident_id == incident.id).order_by(TimelineEvent.timestamp)).all()
    actions = session.exec(select(ProposedAction).where(ProposedAction.incident_id == incident.id)).all()
    similar = session.exec(select(Incident).where(Incident.id != incident.id, Incident.category == incident.category)).all()
    data = serialize(incident)
    data.update({"timeline": [serialize(row) for row in events], "evidence": [serialize(row) for row in logs], "proposed_actions": [serialize(row) for row in actions], "similar_incidents": [serialize(row) for row in similar[:3]]})
    return data


def run_analysis(session: Session, incident: Incident) -> None:
    logs = session.exec(select(LogEntry).where(LogEntry.incident_id == incident.id).order_by(LogEntry.timestamp)).all()
    result = analyze_incident(incident.description, [serialize(row) for row in logs])
    incident.category = result.category
    incident.severity = result.severity
    incident.priority = result.priority
    incident.confidence = result.confidence
    incident.ai_summary = result.summary
    incident.probable_root_cause = result.probable_root_cause
    session.add(incident)
    evidence = set(result.evidence_log_ids)
    session.add(TimelineEvent(incident_id=incident.id, actor="ai", type="analysis", detail=result.summary, evidence_ids=sorted(evidence)))
    for proposal in result.proposed_actions:
        session.add(ProposedAction(incident_id=incident.id, description=proposal.description, risk=Risk(proposal.risk)))
    if any(proposal.risk == "sensitive" for proposal in result.proposed_actions):
        transition(session, incident, IncidentStatus.AWAITING_APPROVAL, actor="system")
    append_audit(session, "ai", "incident.analysis_created", {"incident_id": incident.id, "category": result.category, "severity": result.severity, "confidence": result.confidence, "evidence_log_ids": result.evidence_log_ids, "summary": result.summary})


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/incidents")
def create_incident(body: IncidentCreate, session: Session = Depends(get_session)):
    incident = Incident(title=body.title, description=body.description, source=body.source, service=body.service)
    session.add(incident)
    session.flush()
    append_audit(session, "user", "incident.created", {"incident_id": incident.id, "source": body.source})
    session.add(TimelineEvent(incident_id=incident.id, actor="user", type="created", detail="Incident created."))
    transition(session, incident, IncidentStatus.TRIAGED)
    transition(session, incident, IncidentStatus.INVESTIGATING)
    run_analysis(session, incident)
    session.commit()
    session.refresh(incident)
    return incident_detail(session, incident)


@app.get("/incidents")
def list_incidents(status: IncidentStatus | None = None, severity: str | None = None, category: str | None = None, service: str | None = None, q: str | None = Query(default=None), session: Session = Depends(get_session)):
    rows = session.exec(select(Incident).order_by(Incident.created_at.desc())).all()
    if status:
        rows = [row for row in rows if row.status == status]
    if severity:
        rows = [row for row in rows if row.severity == severity]
    if category:
        rows = [row for row in rows if row.category.lower() == category.lower()]
    if service:
        rows = [row for row in rows if row.service and row.service.lower() == service.lower()]
    if q:
        needle = q.lower()
        rows = [row for row in rows if needle in f"{row.title} {row.description} {row.service or ''}".lower()]
    return [serialize(row) for row in rows]


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str, session: Session = Depends(get_session)):
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident_detail(session, incident)


@app.patch("/incidents/{incident_id}")
def patch_incident(incident_id: str, body: IncidentPatch, session: Session = Depends(get_session)):
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    changes: dict[str, dict[str, Any]] = {}
    for field in ("title", "description", "source", "service"):
        if field in body.model_fields_set:
            value = getattr(body, field)
            if value is None and field != "service":
                raise HTTPException(422, f"{field} cannot be null")
            previous = getattr(incident, field)
            if previous != value:
                setattr(incident, field, value)
                changes[field] = {"from": previous, "to": value}
    if changes:
        append_audit(session, "user", "incident.updated", {"incident_id": incident.id, "changes": changes})
        session.add(TimelineEvent(incident_id=incident.id, actor="user", type="updated", detail=f"Updated fields: {', '.join(changes)}."))
    if body.status and body.status != incident.status:
        try:
            transition(session, incident, body.status, actor="user")
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
    if "assignee" in body.model_fields_set and incident.assignee != body.assignee:
        incident.assignee = body.assignee
        append_audit(session, "user", "incident.assigned", {"incident_id": incident.id, "assignee": body.assignee})
        session.add(TimelineEvent(incident_id=incident.id, actor="user", type="assignment", detail=f"Assigned to {body.assignee}."))
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident_detail(session, incident)


@app.delete("/incidents/{incident_id}")
def delete_incident(incident_id: str, session: Session = Depends(get_session)):
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    for model in (LogEntry, TimelineEvent, ProposedAction):
        for child in session.exec(select(model).where(model.incident_id == incident_id)).all():
            session.delete(child)
    append_audit(session, "user", "incident.deleted", {"incident_id": incident_id, "title": incident.title})
    session.delete(incident)
    session.commit()
    return {"deleted": True, "incident_id": incident_id}


@app.post("/incidents/{incident_id}/actions")
def create_action(incident_id: str, body: ActionCreate, session: Session = Depends(get_session)):
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    if incident.status not in {IncidentStatus.INVESTIGATING, IncidentStatus.AWAITING_APPROVAL}:
        raise HTTPException(409, "Actions can only be proposed for incidents under investigation")
    action = ProposedAction(incident_id=incident.id, description=body.description, risk=body.risk)
    session.add(action)
    session.flush()
    session.add(TimelineEvent(incident_id=incident.id, actor="user", type="action_proposed", detail=f"Action proposed ({body.risk.value}): {body.description}"))
    append_audit(session, "user", "action.proposed", {"incident_id": incident.id, "action_id": action.id, "risk": body.risk.value, "description": body.description})
    if body.risk == Risk.SENSITIVE and incident.status == IncidentStatus.INVESTIGATING:
        transition(session, incident, IncidentStatus.AWAITING_APPROVAL, actor="system")
    session.commit()
    session.refresh(action)
    return serialize(action)


@app.post("/logs/ingest")
def ingest_logs(body: LogBatch, session: Session = Depends(get_session)):
    rows = [LogEntry(timestamp=item.timestamp or utcnow(), service=item.service, level=item.level.upper(), message=item.message, trace_id=item.trace_id) for item in body.logs]
    session.add_all(rows)
    append_audit(session, "simulator", "logs.ingested", {"count": len(rows), "log_ids": [row.id for row in rows]})
    session.commit()
    return {"ingested": len(rows), "log_ids": [row.id for row in rows]}


@app.post("/alerts/webhook")
def alert_webhook(body: AlertInput, session: Session = Depends(get_session)):
    incident = Incident(title=body.title, description=body.description, source="alert", service=body.service, severity=body.severity or "SEV3")
    session.add(incident)
    session.flush()
    append_audit(session, "alert_webhook", "incident.created", {"incident_id": incident.id})
    session.add(TimelineEvent(incident_id=incident.id, actor="system", type="alert_received", detail="Alert received through webhook."))
    transition(session, incident, IncidentStatus.TRIAGED)
    transition(session, incident, IncidentStatus.INVESTIGATING)
    run_analysis(session, incident)
    session.commit()
    session.refresh(incident)
    return incident_detail(session, incident)


def decide_action(action_id: str, body: Decision, approve: bool, session: Session):
    action = session.get(ProposedAction, action_id)
    if not action:
        raise HTTPException(404, "Action not found")
    if action.status != ActionStatus.PENDING:
        raise HTTPException(409, "Action is no longer pending")
    incident = session.get(Incident, action.incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    if approve and action.risk == Risk.SENSITIVE and incident.status not in {
        IncidentStatus.INVESTIGATING,
        IncidentStatus.AWAITING_APPROVAL,
    }:
        raise HTTPException(409, "Sensitive action cannot be approved in the incident's current state")
    action.status = ActionStatus.APPROVED if approve else ActionStatus.REJECTED
    action.decided_by = body.decided_by
    action.decided_at = utcnow()
    incident = session.get(Incident, action.incident_id)
    if approve and action.risk == Risk.SENSITIVE:
        # The hackathon simulator records an approved rollback as executed; it never
        # reaches an external deployment system.
        if incident.status == IncidentStatus.INVESTIGATING:
            incident = transition(session, incident, IncidentStatus.AWAITING_APPROVAL, actor="system")
        action.status = ActionStatus.EXECUTED
        incident = transition(session, incident, IncidentStatus.MITIGATED, actor=body.decided_by)
        incident = transition(session, incident, IncidentStatus.RESOLVED, actor="simulator")
    elif not approve and action.risk == Risk.SENSITIVE and incident.status == IncidentStatus.AWAITING_APPROVAL:
        other_pending = session.exec(
            select(ProposedAction).where(
                ProposedAction.incident_id == incident.id,
                ProposedAction.risk == Risk.SENSITIVE,
                ProposedAction.status == ActionStatus.PENDING,
                ProposedAction.id != action.id,
            )
        ).first()
        if other_pending is None:
            incident = transition(session, incident, IncidentStatus.INVESTIGATING, actor="system")
    session.add(action)
    detail = f"{'Approved' if approve else 'Rejected'}: {action.description}"
    session.add(TimelineEvent(incident_id=action.incident_id, actor=body.decided_by, type="action_decision", detail=detail))
    append_audit(session, body.decided_by, "action.approved" if approve else "action.rejected", {"action_id": action.id, "incident_id": action.incident_id, "risk": action.risk.value, "simulated_execution": bool(approve and action.risk == Risk.SENSITIVE)})
    session.commit()
    session.refresh(action)
    return {"action": serialize(action), "incident": incident_detail(session, incident)}


@app.post("/actions/{action_id}/approve")
def approve_action(action_id: str, body: Decision, session: Session = Depends(get_session)):
    return decide_action(action_id, body, True, session)


@app.post("/actions/{action_id}/reject")
def reject_action(action_id: str, body: Decision, session: Session = Depends(get_session)):
    return decide_action(action_id, body, False, session)


@app.post("/incidents/{incident_id}/postmortem")
def postmortem(incident_id: str, session: Session = Depends(get_session)):
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    logs = session.exec(select(LogEntry).where(LogEntry.incident_id == incident.id).order_by(LogEntry.timestamp)).all()
    events = session.exec(select(TimelineEvent).where(TimelineEvent.incident_id == incident.id).order_by(TimelineEvent.timestamp)).all()
    draft = {
        "title": f"Postmortem: {incident.title}", "status": "draft",
        "impact": incident.description,
        "root_cause": incident.probable_root_cause,
        "detection": "Incident detected from simulated failure injection or incoming alert.",
        "resolution": "Rollback was recorded as a simulated action after human approval." if incident.resolved_at else "Incident remains open; document the approved mitigation after resolution.",
        "timeline": [{"timestamp": row.timestamp.isoformat(), "event": row.detail} for row in events],
        "evidence_log_ids": [row.id for row in logs],
        "follow_up": ["Add a deployment guard for connection-pool saturation", "Alert on sustained checkout 5xx rate", "Review pool limits and retry behavior"],
    }
    append_audit(session, "ai", "postmortem.drafted", {"incident_id": incident.id, "evidence_log_ids": draft["evidence_log_ids"]})
    session.add(TimelineEvent(incident_id=incident.id, actor="ai", type="postmortem_drafted", detail="AI drafted a postmortem for human review."))
    session.commit()
    return draft


@app.post("/simulate/{scenario}")
def simulate(scenario: str, session: Session = Depends(get_session)):
    if scenario != "bad-deploy-checkout":
        raise HTTPException(404, "Unknown scenario")
    incident = inject_bad_deploy(session)
    append_audit(session, "simulator", "scenario.injected", {"scenario": scenario, "incident_id": incident.id})
    session.commit()
    session.refresh(incident)
    return incident_detail(session, incident)


@app.get("/kb")
def list_kb(q: str | None = None, session: Session = Depends(get_session)):
    rows = session.exec(select(KBArticle).order_by(KBArticle.title)).all()
    if q:
        needle = q.lower()
        rows = [row for row in rows if needle in f"{row.title} {row.category} {row.content_md}".lower()]
    return [serialize(row) for row in rows]


@app.get("/analytics")
def analytics(session: Session = Depends(get_session)):
    rows = session.exec(select(Incident)).all()
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    durations = []
    for row in rows:
        by_severity[row.severity] = by_severity.get(row.severity, 0) + 1
        by_category[row.category] = by_category.get(row.category, 0) + 1
        if row.resolved_at:
            durations.append((row.resolved_at - row.created_at).total_seconds())
    return {"total_incidents": len(rows), "by_severity": by_severity, "by_category": by_category, "mttr_seconds": sum(durations) / len(durations) if durations else None, "resolved_count": len(durations)}


@app.get("/audit")
def audit(session: Session = Depends(get_session)):
    rows = session.exec(select(AuditLog).order_by(AuditLog.sequence)).all()
    return {"verified": verify_chain(rows), "events": [serialize(row) for row in rows]}
