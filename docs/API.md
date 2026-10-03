# PS-61 Incident Response Agent API

Base URL: `http://localhost:8000`

Responses are JSON. Timestamps use UTC ISO-8601. Interactive OpenAPI docs are available at `/docs`.

## Health

- `GET /health` — returns `{"status":"ok"}`.

## Incidents

- `POST /incidents` — create an incident and run initial analysis. Body: `{"title":"Checkout errors","description":"5xx errors after deploy","source":"manual","service":"checkout"}`.
- `GET /incidents` — list incidents. Optional filters: `status`, `severity`, `category`, `service`, and free-text `q`.
- `GET /incidents/{incident_id}` — incident with timeline, evidence logs, proposed actions, and up to three similar incidents.
- `PATCH /incidents/{incident_id}` — update `title`, `description`, `source`, `service`, `status`, and `assignee`; set `service` or `assignee` to `null` to clear them. Lifecycle transitions are validated and changes are recorded in the audit chain. Example: `{"title":"Checkout API","status":"Investigating","assignee":"on-call"}`.
- `DELETE /incidents/{incident_id}` — delete an incident and its logs, timeline events, and proposed actions; the deletion is recorded in the audit chain.
- `POST /incidents/{incident_id}/actions` — propose an action. Body: `{"description":"Roll back release 42","risk":"sensitive"}` (`risk` is `safe` or `sensitive`). Actions can be proposed only while investigating or awaiting approval. Sensitive proposals require human approval and move an investigating incident to `Awaiting Approval`.
- `POST /incidents/{incident_id}/postmortem` — create and return a postmortem draft for review, based on the incident evidence. The draft event is recorded in the timeline and audit chain.

Incident status values: `New`, `Triaged`, `Investigating`, `Awaiting Approval`, `Mitigated`, `Resolved`, `Closed`. Invalid status transitions return HTTP 409. Missing incident IDs return HTTP 404.

## Logs and alerts

- `POST /logs/ingest` — ingest a batch. Body: `{"logs":[{"service":"checkout","level":"ERROR","message":"database timeout","trace_id":"trace-123","timestamp":"2026-10-03T10:00:00Z"}]}`. `timestamp` and `trace_id` are optional.
- `POST /alerts/webhook` — create and analyze an incident from an alert. Body: `{"title":"Checkout 5xx spike","description":"Error rate above threshold","service":"checkout","severity":"SEV2"}`. Fields other than `title` are optional.
- `POST /simulate/bad-deploy-checkout` — inject the built-in demo failure scenario.

## Action approval

- `POST /actions/{action_id}/approve` — approve a pending action. Body: `{"decided_by":"incident-commander"}`. Sensitive actions can be approved only while the incident is investigating or awaiting approval. The demo records the sensitive rollback as simulated execution, then moves the incident through `Mitigated` to `Resolved`; it does not call a deployment system.
- `POST /actions/{action_id}/reject` — reject a pending action. Body: `{"decided_by":"incident-commander"}`. Rejecting the last pending sensitive action returns an awaiting-approval incident to `Investigating`.

A decision on a non-pending action returns HTTP 409. Missing action IDs return HTTP 404.

## Knowledge, analytics, and audit

- `GET /kb` — list knowledge-base articles; optional `q` searches title, category, and content.
- `GET /analytics` — incident totals, counts by severity/category, resolved count, and mean time to resolution (`mttr_seconds`).
- `GET /audit` — audit events and whether the hash chain verifies (`verified`).

## Local setup

From the repository root, run `python -m uvicorn backend.main:app --reload`. The frontend origin `http://localhost:5173` and loopback alias `http://127.0.0.1:5173` are allowed by the API CORS configuration.