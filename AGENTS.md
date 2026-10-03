# AGENTS.md
## Project
AI Software Incident Response Agent (PS-61). 5-hour hackathon build.
## Rules
- Backend: Python 3.11, FastAPI, SQLModel, SQLite. Frontend: React + Vite + Tailwind + shadcn/ui.
- Keep modules small. No auth, no Docker, no real third-party integrations.
- The LLM NEVER executes actions. It only proposes. Sensitive actions require human approval.
- All LLM output must be Pydantic-validated JSON. If the LLM fails, return the rule-based fallback.
- Every AI output and every state change writes to audit_log (hash-chained).
- Run the code and fix errors before stopping. Add a seed script and a simulator.
- Keep /docs/API.md in sync with the endpoints.
## Demo scenario
Bad deploy of checkout-service (v2.4.1) -> DB connection pool exhausted -> 5xx spike ->
incident SEV-1 -> AI finds similar past incident -> proposes Rollback to v2.4.0 (sensitive)
-> human approves -> Mitigated -> Resolved -> AI drafts postmortem.
