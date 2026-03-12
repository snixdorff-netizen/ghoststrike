from __future__ import annotations

from importlib import resources
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from ada_iq.agents import list_agent_specs
from ada_iq.config import load_settings
from ada_iq.orchestrator import Orchestrator
from ada_iq.seeds import ensure_admin_user, seed_demo_projects
from ada_iq.store import SQLiteContextStore


settings = load_settings()
app = FastAPI(title="Ada IQ MVP", version="0.1.0")
store = SQLiteContextStore(settings.database_path)
orchestrator = Orchestrator(store=store)


class AuthRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class AdminCreateUserRequest(AuthRequest):
    role: str = Field(default="MEMBER", pattern="^(ADMIN|MEMBER)$")


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    brief: str = Field(min_length=10)


class DecisionRequest(BaseModel):
    approved: bool
    feedback: str | None = None


class WorkflowRequest(BaseModel):
    approval_feedback: str = "Proceed to IDEATE"


class CollaboratorRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    access_role: str = Field(pattern="^(VIEWER|EDITOR)$")


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=10)


class FeedbackRequest(BaseModel):
    summary: str = Field(min_length=5, max_length=1000)
    category: str = Field(default="GENERAL", max_length=80)


def _read_static_file(filename: str) -> str:
    return resources.files("ada_iq").joinpath("static", filename).read_text(encoding="utf-8")


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    return authorization.split(" ", 1)[1].strip()


def current_user(authorization: str | None = Header(default=None)) -> dict:
    token = _extract_token(authorization)
    try:
        return orchestrator.get_user_for_token(token)
    except KeyError as exc:
        raise HTTPException(status_code=401, detail="Invalid session.") from exc


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


@app.on_event("startup")
def bootstrap_demo_data() -> None:
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        ensure_admin_user(orchestrator, settings.bootstrap_admin_email, settings.bootstrap_admin_password)
    if settings.demo_account_enabled:
        ensure_admin_user(orchestrator, settings.demo_account_email, settings.demo_account_password)
    if settings.auto_seed_demo:
        seed_demo_projects(
            orchestrator,
            settings.seed_data_path,
            owner_email=settings.bootstrap_admin_email or "demo@adaiq.local",
            owner_password=settings.bootstrap_admin_password or "demo12345",
        )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _read_static_file("index.html")


@app.get("/app.css")
def app_css() -> str:
    return Response(content=_read_static_file("app.css"), media_type="text/css")


@app.get("/app.js")
def app_js() -> str:
    return Response(content=_read_static_file("app.js"), media_type="application/javascript")


@app.get("/ui")
def ui_redirect() -> RedirectResponse:
    return RedirectResponse(url="/")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register")
def register(request: AuthRequest) -> dict:
    if not settings.open_registration:
        raise HTTPException(status_code=403, detail="Open registration is disabled for the alpha.")
    try:
        return orchestrator.register_user(request.email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/auth/login")
def login(request: AuthRequest) -> dict:
    try:
        return orchestrator.login_user(request.email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/auth/logout")
def logout(user: dict = Depends(current_user), authorization: str | None = Header(default=None)) -> dict:
    token = _extract_token(authorization)
    orchestrator.logout_user(token)
    return {"status": "ok", "user_id": user["user_id"]}


@app.get("/me")
def me(user: dict = Depends(current_user)) -> dict:
    return user


@app.get("/admin/users")
def admin_list_users(user: dict = Depends(admin_user)) -> list[dict]:
    return orchestrator.list_users(user["user_id"])


@app.post("/admin/users")
def admin_create_user(request: AdminCreateUserRequest, user: dict = Depends(admin_user)) -> dict:
    try:
        return orchestrator.admin_create_user(user["user_id"], request.email, request.password, request.role)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/admin/projects")
def admin_list_projects(user: dict = Depends(admin_user)) -> list[dict]:
    return orchestrator.list_all_projects(user["user_id"])


@app.post("/projects")
def create_project(request: CreateProjectRequest, user: dict = Depends(current_user)) -> dict:
    project = orchestrator.create_project(owner_user_id=user["user_id"], name=request.name, brief=request.brief)
    return orchestrator.get_project_snapshot(project.project_id, user["user_id"])


@app.get("/projects")
def list_projects(user: dict = Depends(current_user)) -> list[dict]:
    return orchestrator.list_projects_snapshot(user["user_id"])


@app.get("/projects/{project_id}/runs")
def list_project_runs(project_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return orchestrator.get_project_snapshot(project_id, user["user_id"])["runs"]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/projects/{project_id}/jobs")
def list_project_jobs(project_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return orchestrator.get_project_snapshot(project_id, user["user_id"])["jobs"]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/projects/{project_id}/events")
def list_project_events(project_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return orchestrator.get_project_snapshot(project_id, user["user_id"])["events"]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/projects/{project_id}/export")
def export_project(project_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.export_project_snapshot(project_id, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/projects/{project_id}/collaborators")
def list_project_collaborators(project_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return orchestrator.list_project_collaborators(project_id, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/projects/{project_id}/collaborators")
def add_project_collaborator(project_id: str, request: CollaboratorRequest, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.add_project_collaborator(project_id, user["user_id"], request.email, request.access_role)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project or user not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/projects/{project_id}/invitations")
def list_project_invitations(project_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return orchestrator.list_project_invitations(project_id, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/projects/{project_id}/invitations")
def invite_project_collaborator(project_id: str, request: CollaboratorRequest, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.invite_project_collaborator(project_id, user["user_id"], request.email, request.access_role)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/invitations/accept")
def accept_invitation(request: InvitationAcceptRequest, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.accept_invitation(request.token, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Invitation not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/projects/{project_id}/feedback")
def list_project_feedback(project_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return orchestrator.list_project_feedback(project_id, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/projects/{project_id}/feedback")
def submit_project_feedback(project_id: str, request: FeedbackRequest, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.submit_project_feedback(project_id, user["user_id"], request.summary, request.category)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/meta/agents")
def get_agent_specs() -> list[dict[str, str]]:
    return list_agent_specs()


@app.get("/meta/architecture")
def get_architecture_summary() -> dict:
    return {
        "sprint": "1.0",
        "capabilities": [
            "User can create a project from a brief",
            "User can run the current DFN phase",
            "User can inspect agent outputs and message history",
            "User can approve or reject human gates",
            "Project state persists in SQLite",
            "Projects are scoped to authenticated users",
            "Admin users can inspect platform-wide users and projects",
            "Admin users can create alpha-user accounts",
            "Owners can share projects with viewers and editors",
            "Owners can issue invitation tokens for collaborators",
            "Users can submit project-level alpha feedback",
        ],
        "tech_stack": {
            "api": "FastAPI",
            "orchestrator": "Typed Python service layer",
            "persistence": "SQLite",
            "frontend": "Static HTML/CSS/JavaScript served by FastAPI",
            "tests": "Standard-library unittest",
        },
        "next_targets": [
            "External queue worker replacing the in-process demo worker",
            "PostgreSQL context store",
            "Email-backed invitation delivery",
            "Password reset and onboarding flow",
            "Role-based access control",
        ],
    }


@app.get("/meta/access")
def get_access_summary() -> dict:
    return {
        "open_registration": settings.open_registration,
        "alpha_mode": not settings.open_registration,
        "build_label": settings.build_label,
        "demo_account_enabled": settings.demo_account_enabled,
        "demo_account_email": settings.demo_account_email if settings.demo_account_enabled else None,
        "demo_account_password": settings.demo_account_password if settings.demo_account_enabled else None,
    }


@app.get("/meta/phases")
def get_development_phases() -> list[dict[str, str]]:
    return [
        {"phase": "2", "name": "EMPATHIZE Integrations", "status": "implemented", "focus": "Provider-backed market and consumer intelligence seams."},
        {"phase": "3", "name": "Execution Tracking", "status": "implemented", "focus": "Persistent run history and partner-visible workflow audit trail."},
        {"phase": "4", "name": "Partner Review Exports", "status": "implemented", "focus": "Project export endpoints and packaged deployment for evaluation."},
        {"phase": "5", "name": "Operational Readiness", "status": "in_progress", "focus": "Queue abstraction, structured event logs, and richer operator visibility."},
        {"phase": "6", "name": "Authentication", "status": "implemented", "focus": "Local auth, session tokens, and per-user project ownership."},
        {"phase": "7", "name": "Collaboration", "status": "implemented", "focus": "Project viewers/editors and shared workflow access."},
    ]


@app.post("/projects/{project_id}/start")
def start_project(project_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        orchestrator.start_current_phase(project_id, owner_user_id=user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return orchestrator.get_project_snapshot(project_id, user["user_id"])


@app.post("/projects/{project_id}/queue")
def enqueue_project_phase(project_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.enqueue_current_phase(project_id, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/jobs/{job_id}/process")
def process_job(job_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.process_job(job_id, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/projects/{project_id}/decision")
def submit_decision(project_id: str, request: DecisionRequest, user: dict = Depends(current_user)) -> dict:
    try:
        orchestrator.submit_decision(project_id, approved=request.approved, feedback=request.feedback, owner_user_id=user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return orchestrator.get_project_snapshot(project_id, user["user_id"])


@app.post("/projects/{project_id}/flows/first-seven-steps")
def complete_first_seven_steps(project_id: str, request: WorkflowRequest, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.complete_first_seven_steps(project_id, user["user_id"], approval_feedback=request.approval_feedback)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/projects/{project_id}/flows/v1-package")
def complete_v1_workflow(project_id: str, request: WorkflowRequest, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.complete_v1_workflow(project_id, user["user_id"], approval_feedback=request.approval_feedback)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/projects/{project_id}/flows/full-cycle")
def complete_full_cycle(project_id: str, request: WorkflowRequest, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.complete_full_cycle(project_id, user["user_id"], approval_feedback=request.approval_feedback)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/projects/{project_id}")
def get_project(project_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.get_project_snapshot(project_id, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
