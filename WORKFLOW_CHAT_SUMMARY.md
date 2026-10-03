# Incident Agent Workflow Chat Summary

This file captures the project requirements and decisions discussed in the workflow chat so they remain available in the `incident-agent` project folder.

## Project

- AI Software Incident Response Agent (PS-61), built for a five-hour hackathon.
- Backend: Python 3.11, FastAPI, SQLModel, SQLite.
- Frontend: React, Vite, Tailwind, and shadcn/ui.
- Keep modules small. No authentication, Docker, or real third-party integrations.
- LLMs only propose actions; they never execute actions. Sensitive actions require human approval.
- Validate all LLM output as Pydantic JSON; return a rule-based fallback if the LLM fails.
- Write each AI output and state change to a hash-chained audit log.
- Include a seed script and simulator. Keep `/docs/API.md` synchronized with API endpoints.

## Demo Scenario

Bad deploy of checkout-service v2.4.1 causes database connection-pool exhaustion, then a 5xx spike and a SEV-1 incident. AI finds a similar past incident and proposes rollback to v2.4.0. A human approves the sensitive action; the incident moves through Mitigated and Resolved, and AI drafts a postmortem.

## Authorized Track A Backend Scope

The user authorized continuing the full backend implementation while leaving the frontend untouched:

1. Add `Incident.ai_analysis` JSON matching the exact plan schema, update `/docs/API.md`, and safely migrate the existing SQLite database.
2. Add an idempotent seed for 18 resolved historical incidents across Availability, Performance, Security, Data, and Deployment, including database connection-pool-after-deploy and bad-deploy 5xx examples, plus six Markdown knowledge-base runbooks.
3. Add a realistic simulator for `api-gateway → checkout-service → payment-service → postgres`. `generate_normal(30)` should produce about 1% errors. `inject_failure('bad_deploy')` should deploy checkout v2.4.1, trigger postgres `too many connections`, exhaust checkout's pool, produce about 40% gateway 5xx, and share failing trace IDs. Save logs.
4. Add backend pipeline modules for:
   - Drain3 parsing with a non-crashing fallback.
   - Per-service minute error rates with rolling z-score detection above 3.
   - ±5-minute trace, dependency, and deployment correlation.
   - TF-IDF cosine similarity for the top three incidents, including resolutions.
   - Keyword classification.
   - Provider-agnostic `.env` LLM wrapper with a 20-second timeout.
   - Pydantic RCA JSON validation and evidence-ID whitelisting.
   - Always-safe fallback behavior.
   - Orchestration that persists `ai_analysis`, timeline events, and recommended actions; safe simulated auto-execution; sensitive actions pending human approval; valid lifecycle transitions; and hash-chained audit entries for AI output and state changes.
5. Add `POST /incidents/{id}/analyze`, `POST /simulate/bad_deploy`, and `POST /reset` (clear incidents/logs/actions/timeline/audit, then seed).
6. Preserve `.env` and secrets, as well as existing CRUD, approval, and audit behavior.
7. Run the project's required runtime verification and fix failures.

## Access Status

Workspace inspection and execution were attempted repeatedly, but the tools failed before commands could start with `helper_unknown_error: setup refresh had errors`. The IDE connection also failed to start. No project implementation changes were made in those attempts, and runtime verification remains outstanding.

## Chat Archive Note

This is a consolidated record of the workflow conversation, not a verbatim export of the chat transcript.
