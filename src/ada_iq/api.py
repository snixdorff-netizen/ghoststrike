from __future__ import annotations

from importlib import resources
from pathlib import Path
from html import escape

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):  # type: ignore[override]
        response = await call_next(request)
        if settings.security_headers_enabled:
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
            if request.url.scheme == "https":
                response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
            if request.url.path.startswith("/auth") or request.url.path.startswith("/projects/"):
                response.headers.setdefault("Cache-Control", "no-store")
        return response


app.add_middleware(SecurityHeadersMiddleware)


class AuthRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class AdminCreateUserRequest(AuthRequest):
    role: str = Field(default="MEMBER", pattern="^(ADMIN|MEMBER)$")


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    brief: str = Field(min_length=10)
    tenant_id: str = Field(default="preview", min_length=2, max_length=120)
    smart_brief: "SmartBriefRequest | None" = None


class SmartBriefRequest(BaseModel):
    category: str = Field(min_length=2, max_length=120)
    price_point: str = Field(min_length=2, max_length=120)
    consumer_profile: str = Field(min_length=5, max_length=240)
    geo_market: str = Field(min_length=2, max_length=120)
    competitive_set: list[str] = Field(default_factory=list)
    brand_guardrails: str = Field(default="", max_length=500)
    constraints: str = Field(default="", max_length=500)
    launch_season: str = Field(default="", max_length=120)
    uploaded_docs: list[str] = Field(default_factory=list)
    open_context: str = Field(default="", max_length=2000)


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


class SmartBriefModuleUpdateRequest(BaseModel):
    content: str = Field(min_length=10, max_length=5000)


def _read_static_file(filename: str) -> str:
    return resources.files("ada_iq").joinpath("static", filename).read_text(encoding="utf-8")


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    return authorization.split(" ", 1)[1].strip()


def _render_smart_brief_report(package: dict) -> str:
    modules = "".join(
        f"""
        <section style="margin-bottom:24px;padding:20px;border:1px solid #ddd;border-radius:14px;background:#fff;">
          <h2 style="margin:0 0 12px;font-size:22px;">{escape(module.get('title', 'Module'))}</h2>
          <p style="margin:0 0 12px;line-height:1.7;">{escape(module.get('content', ''))}</p>
          <p style="margin:0 0 8px;color:#666;font-size:14px;">Version {escape(str(module.get('version', 1)))} · Updated by {escape(module.get('updated_by', 'system'))}</p>
          <p style="margin:0;color:#666;font-size:14px;">Citations: {escape(', '.join(module.get('citations', [])) or 'None')}</p>
        </section>
        """
        for module in package.get("modules", [])
    )
    supporting_outputs = "".join(
        f"<li style=\"margin-bottom:8px;\">{escape(item.get('output_type', 'output'))} · {escape(item.get('data', {}).get('summary', ''))}</li>"
        for item in package.get("supporting_outputs", [])
    )
    compliance = package.get("compliance", {})
    return f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{escape(package.get('project_name', 'Ada Brief'))}</title>
        <style>
          @media print {{
            .report-toolbar {{ display:none !important; }}
            body {{ background:#fff !important; }}
          }}
        </style>
      </head>
      <body style="margin:0;padding:40px;background:#f6f4f1;color:#161616;font-family:Inter,Arial,sans-serif;">
        <main style="max-width:980px;margin:0 auto;">
          <div class="report-toolbar" style="display:flex;justify-content:flex-end;margin-bottom:16px;">
            <button onclick="window.print()" style="border:1px solid #ddd;background:#fff;padding:10px 14px;border-radius:10px;cursor:pointer;">Print / Save PDF</button>
          </div>
          <header style="margin-bottom:32px;padding:28px;border-radius:20px;background:#111;color:#fff;">
            <p style="margin:0 0 10px;color:#f25b6b;letter-spacing:.14em;text-transform:uppercase;font-size:12px;">{escape(settings.report_brand_title)} Ada Brief</p>
            <h1 style="margin:0 0 12px;font-size:42px;line-height:1.1;">{escape(package.get('project_name', 'Project'))}</h1>
            <p style="margin:0;line-height:1.7;color:#ddd;">{escape(package.get('summary', ''))}</p>
          </header>
          <section style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:24px;">
            <article style="padding:18px;border-radius:16px;background:#fff;border:1px solid #ddd;"><strong>Tenant</strong><p>{escape(package.get('tenant_id', 'preview'))}</p></article>
            <article style="padding:18px;border-radius:16px;background:#fff;border:1px solid #ddd;"><strong>Classification</strong><p>{escape(compliance.get('data_classification', 'CONFIDENTIAL'))}</p></article>
            <article style="padding:18px;border-radius:16px;background:#fff;border:1px solid #ddd;"><strong>Compliance</strong><p>{escape(compliance.get('status', 'TRACKED'))}</p></article>
          </section>
          <section style="margin-bottom:24px;padding:20px;border:1px solid #ddd;border-radius:14px;background:#fff;">
            <h2 style="margin:0 0 12px;font-size:22px;">Supporting Intelligence</h2>
            <ul style="margin:0;padding-left:18px;line-height:1.7;">{supporting_outputs or '<li>No supporting outputs yet.</li>'}</ul>
          </section>
          {modules}
        </main>
      </body>
    </html>
    """


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


@app.post("/auth/demo")
def demo_login() -> dict:
    if not settings.demo_account_enabled or not settings.public_demo_access_enabled:
        raise HTTPException(status_code=403, detail="Public demo access is disabled.")
    try:
        return orchestrator.create_session_for_email(settings.demo_account_email)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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


@app.get("/admin/dashboard")
def admin_dashboard(user: dict = Depends(admin_user)) -> dict:
    summary = orchestrator.get_admin_dashboard(user["user_id"])
    summary["build_label"] = settings.build_label
    return summary


@app.post("/projects")
def create_project(request: CreateProjectRequest, user: dict = Depends(current_user)) -> dict:
    project = orchestrator.create_project(
        owner_user_id=user["user_id"],
        name=request.name,
        brief=request.brief,
        smart_brief=request.smart_brief.model_dump() if request.smart_brief else None,
        tenant_id=request.tenant_id,
    )
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


@app.get("/projects/{project_id}/smart-brief")
def export_smart_brief(project_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.get_smart_brief_package(project_id, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.patch("/projects/{project_id}/smart-brief/modules/{module_key}")
def update_smart_brief_module(project_id: str, module_key: str, request: SmartBriefModuleUpdateRequest, user: dict = Depends(current_user)) -> dict:
    try:
        return orchestrator.update_smart_brief_module(project_id, module_key, request.content, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project or module not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/projects/{project_id}/smart-brief/report", response_class=HTMLResponse)
def smart_brief_report(project_id: str, user: dict = Depends(current_user)) -> str:
    try:
        package = orchestrator.get_smart_brief_package(project_id, user["user_id"])
        return _render_smart_brief_report(package)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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
        "public_demo_access_enabled": settings.public_demo_access_enabled,
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


@app.get("/meta/compliance")
def get_compliance_summary() -> dict:
    return {
        "framework": "SOC 2 readiness track",
        "security_headers_enabled": settings.security_headers_enabled,
        "controls": [
            {"id": "CC6.1", "name": "Logical access controls", "status": "implemented"},
            {"id": "CC6.6", "name": "Audit logging and traceability", "status": "implemented"},
            {"id": "CC7.2", "name": "Change monitoring and issue response", "status": "in_progress"},
            {"id": "CC8.1", "name": "Change management", "status": "tracked"},
            {"id": "PI1.1", "name": "Data classification and retention", "status": "implemented"},
        ],
        "platform_guards": [
            "tenant-aware project records",
            "governance metadata on outputs, jobs, and events",
            "security response headers",
            "versioned Smart Product Brief modules",
            "admin and activity audit trail",
        ],
    }


@app.get("/meta/smart-brief")
def get_smart_brief_schema() -> dict:
    return {
        "product": "Smart Product Brief",
        "status": "foundation",
        "entry_fields": [
            "category",
            "price_point",
            "consumer_profile",
            "geo_market",
            "competitive_set",
            "brand_guardrails",
            "constraints",
            "launch_season",
            "uploaded_docs",
            "open_context",
        ],
        "generated_modules": [
            "Executive Summary",
            "Consumer Insight",
            "Market Context",
            "Competitive Intelligence",
            "Trend Signal",
            "Strategic Directions",
            "Design Requirements",
            "Technical Constraints",
            "Success Metrics",
        ],
        "compliance_tracking": [
            "tenant_id",
            "data_classification",
            "soc2_controls",
            "compliance_status",
        ],
    }


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
