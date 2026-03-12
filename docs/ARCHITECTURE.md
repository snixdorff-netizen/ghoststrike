# Sprint 1.0 Architecture

This repository now exposes a reviewable Sprint 1.0 vertical slice for Ada IQ.

## Scope

The current code supports:

- persistent project creation
- orchestrated DFN phase execution
- agent output capture
- human decision gates
- browser-based interaction
- partner-facing metadata endpoints
- two provider-backed specialist integration seams
- in-process queue and structured event logging
- dedicated worker process for queued execution
- local auth and per-user project ownership
- basic admin/member role separation
- project-level viewer/editor collaboration
- invitation-based collaboration onboarding
- closed-signup alpha mode with admin-created user provisioning
- project-level feedback capture through the event log

## System Shape

### Backend

- `ada_iq.api`: HTTP routes, UI delivery, and metadata endpoints
- `ada_iq.orchestrator`: workflow sequencing and gate control
- `ada_iq.agents`: specialist agent registry and deterministic stubs
- `ada_iq.providers`: provider modules that model external service integrations
- `ada_iq.store`: storage abstraction with SQLite persistence
- `ada_iq.queue`: in-process job queue abstraction
- `ada_iq.observability`: structured event logging
- `ada_iq.auth`: local password hashing and bearer-session handling
- `ada_iq.models`: domain contracts for projects, messages, outputs, and gates

### Frontend

- static HTML/CSS/JS served directly from the Python package
- no frontend build step
- minimal dependency surface for partner code review

## Why This Sprint Cut Works

- Users can interact with the product in a browser.
- Technical partners can inspect a small, typed codebase without framework sprawl.
- The separation between orchestration, storage, and agent execution is visible and testable.
- Two specialist agents now demonstrate real adapter boundaries rather than only local stubbing.
- The persistence story is concrete, but still easy to swap for PostgreSQL later.
- Execution runs are now persisted, which makes workflow history visible to reviewers.
- Operational behavior is visible through queued jobs and event logs.
- Shared access is scoped by authenticated user rather than one global project list.
- Admin users can inspect platform-wide users and projects.
- Owners can share projects with readers and editors for collaborative testing.
- Invitation and queue activity now record named actors in the event log.

## Known Limits

- Only the Market Intelligence and Consumer Insights paths have provider-backed integration seams today.
- The worker is a SQLite-backed polling process, not a production queue backend.
- RBAC is minimal: `ADMIN` and `MEMBER` only.
- Collaboration is project-scoped and does not yet include comments or approval assignments by named role.
