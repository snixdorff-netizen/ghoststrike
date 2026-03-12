# Ada IQ Sprint 1.0

This repository now contains a Sprint 1.0 vertical slice of the Ada IQ agent platform described in `/Users/stuartnixdorff/Downloads/ada_iq_agent_architecture_workplan (1).docx`.

The current implementation is reviewable by both end users and technical partners:

- DFN phase state machine
- Standardized message bus envelope
- Standardized agent output envelope
- SQLite-backed project context store with versioned outputs
- Human decision gates between DFN phases
- Provider-backed Market Intelligence and Consumer Insights agents plus stubs for the remaining specialist agents
- FastAPI service for creating and advancing projects
- Browser-based product UI for project creation, workflow control, and output review
- Metadata endpoints for agent roster and architecture summary
- Queue and event-log surfaces for operational review
- Local authentication and per-user project ownership
- Basic roles: `ADMIN` and `MEMBER`
- Project-level collaboration with `VIEWER` and `EDITOR` access
- Invitation-based collaborator onboarding
- Dedicated worker process for queued phase execution
- Browser-based admin and operator surfaces for users, projects, jobs, and events
- Closed-signup alpha mode with admin-created users
- In-product alpha feedback capture per project

## What This Is

This is not the full production system. It is the first sprint cut that lets you:

1. Create a project from a brief.
2. Execute the assigned agents for the current DFN phase.
3. Collect structured outputs and messages.
4. Pause at a human approval gate.
5. Approve the gate and continue through the next phase.
6. Interact with the product in a browser.

That aligns with the workplan's early delivery goals: establish the orchestrator, contracts, state handling, persistence, testing, and a path to later integrations like Redis, PostgreSQL, Onshape, and proprietary Ada IQ models.

## Integration Status

- `Ada Scout` is now routed through a provider module in [src/ada_iq/providers/market_intelligence.py](/Users/stuartnixdorff/Documents/New%20project/src/ada_iq/providers/market_intelligence.py). It is still deterministic, but it exposes a real adapter boundary with typed request/response behavior, structured outputs, and fallback-friendly wiring.
- `Ada Empath` is now routed through [src/ada_iq/providers/consumer_insights.py](/Users/stuartnixdorff/Documents/New%20project/src/ada_iq/providers/consumer_insights.py), with a distinct persona and need-state contract.
- The remaining specialist agents still use deterministic stub behavior through [src/ada_iq/agents.py](/Users/stuartnixdorff/Documents/New%20project/src/ada_iq/agents.py).

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn ada_iq.api:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to use the UI.

The app auto-seeds demo projects on first run when the database is empty.
For alpha deployment, set `ADA_IQ_BOOTSTRAP_ADMIN_EMAIL` and `ADA_IQ_BOOTSTRAP_ADMIN_PASSWORD` so first boot creates your real admin account.
Open registration is disabled by default for alpha sharing. Admins create tester accounts from the browser or API.
If no bootstrap admin is configured and seeding is enabled, the fallback seeded admin remains `demo@adaiq.local` / `demo12345`.
You can label each deployed build with `ADA_IQ_BUILD_LABEL` and explicitly enable the public demo account with `ADA_IQ_ENABLE_DEMO_ACCOUNT=true`.

### One-Command Demo

```bash
cp .env.example .env
docker compose up --build
```

That starts the app with a persistent SQLite volume in `./data` and preloads demo projects for partner evaluation.

### Local Script

```bash
sh scripts/start_demo.sh
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## API

`POST /auth/register`

Creates a local account and returns a bearer token when open registration is enabled.

`POST /auth/login`

Signs in and returns a bearer token.

`POST /auth/logout`

Invalidates the current bearer token.

`GET /me`

Returns the authenticated user record.

`GET /admin/users`

Admin-only endpoint returning all users.

`POST /admin/users`

Admin-only endpoint to create alpha-user accounts with a role and temporary password.

`GET /admin/projects`

Admin-only endpoint returning all projects across users.

`GET /projects/{project_id}/collaborators`

Returns project collaborators for users who can access the project.

`POST /projects/{project_id}/collaborators`

Owner-only endpoint to add a collaborator as `VIEWER` or `EDITOR`.

`GET /projects/{project_id}/invitations`

Owner-only endpoint returning invitation records for the project.

`POST /projects/{project_id}/invitations`

Owner-only endpoint to create an invitation token for a new collaborator.

`POST /invitations/accept`

Accepts an invitation token for the authenticated user and grants shared access.

`GET /projects/{project_id}/feedback`

Returns project-level alpha feedback entries for authorized users.

`POST /projects/{project_id}/feedback`

Creates a project-level alpha feedback entry tied to the authenticated user.

`POST /projects`

Example body:

```json
{
  "name": "Cole Haan pilot",
  "brief": "Launch an AI-native footwear product development cycle."
}
```

`POST /projects/{project_id}/start`

Runs all specialist agents assigned to the current DFN phase and opens a human decision gate.

`POST /projects/{project_id}/decision`

Example body:

```json
{
  "approved": true,
  "feedback": "Proceed to the next phase."
}
```

`POST /projects/{project_id}/flows/first-seven-steps`

Runs the early product-development workflow through the first seven steps and returns a bundled package covering EMPATHIZE plus IDEATE.

Example body:

```json
{
  "approval_feedback": "Proceed to IDEATE"
}
```

`POST /projects/{project_id}/flows/v1-package`

Runs the broader v1 workflow through EMPATHIZE, IDEATE, EVALUATE, and REALIZE, returning the consolidated product package.

`POST /projects/{project_id}/flows/full-cycle`

Runs the full DFN cycle through MEASURE and returns the final package, including risk, expansion, and executive synthesis outputs.

`GET /projects/{project_id}`

Returns project state, phase, gate status, messages, and output history.

`GET /projects`

Returns all known projects from the persistent store.

`GET /projects/{project_id}/runs`

Returns the phase execution history for a project.

`GET /projects/{project_id}/jobs`

Returns queued and completed operational jobs for a project.

`GET /projects/{project_id}/events`

Returns structured event logs for a project.

`GET /projects/{project_id}/export`

Returns a partner-facing export snapshot with project state, outputs, messages, and review notes.

`POST /projects/{project_id}/queue`

Queues execution of the current phase without processing it immediately.

`POST /jobs/{job_id}/process`

Processes a queued phase-execution job directly. The packaged demo also includes a dedicated worker process via `python -m ada_iq.worker`.

## Example Endpoint

For an end-to-end early workflow demo, use:

`POST /projects/{project_id}/flows/first-seven-steps`

This endpoint completes:

1. Market sizing
2. Competitive landscape
3. Customer persona
4. Industry trends
5. SWOT and Porter-style strategy
6. Pricing and opportunity framing
7. Concept generation

For the broader v1 demo, use:

`POST /projects/{project_id}/flows/v1-package`

This expands the package to include:

8. Evaluation and concept scoring
9. GTM planning
10. Financial modeling

For the full-cycle demo, use:

`POST /projects/{project_id}/flows/full-cycle`

This adds:

11. Risk assessment
12. Expansion planning
13. Executive synthesis

`GET /meta/agents`

Returns the 12 specialist agent definitions used in Sprint 1.0.

`GET /meta/architecture`

Returns a compact summary of the current architecture and delivery scope.

`GET /meta/access`

Returns the current access mode, including whether open registration is enabled.

`GET /meta/phases`

Returns the current four-phase forward development plan.

## Current Architecture

- `ada_iq.models`: domain models and schema contracts
- `ada_iq.store`: context-store abstraction plus SQLite persistence
- `ada_iq.auth`: local password hashing and session token helpers
- `ada_iq.agents`: specialist agent registry and stubs
- `ada_iq.providers`: external-integration boundaries for specialist agents
- `ada_iq.orchestrator`: phase sequencing and decision-gate logic
- `ada_iq.queue`: in-process job queue abstraction for operational review
- `ada_iq.worker`: dedicated polling worker for queued execution
- `ada_iq.observability`: structured event logging
- `ada_iq.seeds`: deterministic demo dataset loader
- `ada_iq.api`: HTTP service, metadata endpoints, and UI delivery
- `tests/test_alpha.py`: alpha access-control and feedback coverage
- `docs/TEST_PRODUCT_BRIEF.md`: sample project brief for live testing
- `docs/USER_MANUAL.md`: alpha user guide for invited testers
- `tests/test_collaboration.py`: shared-project access coverage
- `docs/ARCHITECTURE.md`: partner-facing system summary
- `docs/ROADMAP.md`: next-phase development plan
- `Dockerfile` + `docker-compose.yml`: partner evaluation runtime

## Immediate Next Steps

- Replace SQLite persistence with PostgreSQL and versioned JSON documents
- Replace the SQLite-backed polling worker with a production queue backend
- Add finer-grained roles and per-project collaboration controls
