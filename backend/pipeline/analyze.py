from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProposedActionOutput(BaseModel):
    description: str
    risk: str = Field(pattern="^(safe|sensitive)$")


class AnalysisOutput(BaseModel):
    category: str
    severity: str = Field(pattern="^SEV[1-4]$")
    priority: int = Field(ge=1, le=4)
    summary: str
    probable_root_cause: str
    confidence: float = Field(ge=0, le=1)
    evidence_log_ids: list[str]
    recommended_steps: list[str]
    proposed_actions: list[ProposedActionOutput]


def rule_based_analysis(description: str, logs: list[dict[str, Any]]) -> AnalysisOutput:
    text = " ".join([description, *(str(row.get("message", "")) for row in logs)]).lower()
    evidence = [str(row["id"]) for row in logs if row.get("id")]
    if "checkout" in text or "connection pool" in text or "5xx" in text:
        return AnalysisOutput(
            category="Availability", severity="SEV1", priority=1,
            summary="Checkout availability degraded after a deployment; correlated errors indicate database connection pressure.",
            probable_root_cause="The recent checkout-service deployment may have exhausted the database connection pool.",
            confidence=0.82 if evidence else 0.62,
            evidence_log_ids=evidence,
            recommended_steps=["Compare error rates before and after the deployment", "Check database pool saturation", "Review recent checkout-service changes"],
            proposed_actions=[ProposedActionOutput(description="Gather deployment and database pool diagnostics", risk="safe"), ProposedActionOutput(description="Rollback checkout-service to the last known good version", risk="sensitive")],
        )
    return AnalysisOutput(
        category="Unknown", severity="SEV3", priority=3,
        summary="An incident was reported; more evidence is needed to identify the cause.",
        probable_root_cause="Insufficient evidence for a reliable root cause.", confidence=0.35,
        evidence_log_ids=evidence,
        recommended_steps=["Collect service logs and recent deployment events", "Check whether customer impact is ongoing"],
        proposed_actions=[ProposedActionOutput(description="Collect recent service logs", risk="safe")],
    )


def analyze_incident(description: str, logs: list[dict[str, Any]]) -> AnalysisOutput:
    # Deterministic fallback is always available. A provider-backed LLM can be added
    # later, but it must return this schema and never execute proposed actions.
    return rule_based_analysis(description, logs)
