from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from ada_iq.models import (
    AgentOutput,
    ComplianceProfile,
    ComplianceStatus,
    DecisionGate,
    DFNPhase,
    EventLog,
    ExecutionRun,
    GateStatus,
    Job,
    JobStatus,
    Message,
    MessageType,
    Project,
    ProjectAccessRole,
    ProjectCollaborator,
    ProjectInvitation,
    ProjectStatus,
    RunStatus,
    Session,
    SmartBriefModule,
    SmartBriefRevision,
    SmartProductBrief,
    User,
    UserRole,
    InvitationStatus,
)


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _deserialize_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _project_to_record(project: Project) -> dict[str, Any]:
    return {
        "project_id": project.project_id,
        "name": project.name,
        "brief": project.brief,
        "owner_user_id": project.owner_user_id,
        "tenant_id": project.tenant_id,
        "smart_brief": json.dumps(dataclass_to_api_dict(project.smart_brief)) if project.smart_brief else None,
        "compliance": json.dumps(dataclass_to_api_dict(project.compliance)),
        "current_phase": project.current_phase.value,
        "status": project.status.value,
        "created_at": _serialize_datetime(project.created_at),
        "updated_at": _serialize_datetime(project.updated_at),
        "gate_phase": project.gate.phase.value,
        "gate_status": project.gate.status.value,
        "gate_feedback": project.gate.feedback,
        "gate_decided_at": _serialize_datetime(project.gate.decided_at),
    }


def _project_from_record(row: sqlite3.Row | dict[str, Any]) -> Project:
    record = dict(row)
    smart_brief_data = json.loads(record["smart_brief"]) if record.get("smart_brief") else None
    compliance_data = json.loads(record["compliance"]) if record.get("compliance") else None
    return Project(
        name=record["name"],
        brief=record["brief"],
        owner_user_id=record["owner_user_id"],
        tenant_id=record.get("tenant_id", "preview"),
        smart_brief=_smart_brief_from_record(smart_brief_data),
        compliance=_compliance_from_record(compliance_data),
        project_id=record["project_id"],
        current_phase=DFNPhase(record["current_phase"]),
        status=ProjectStatus(record["status"]),
        created_at=_deserialize_datetime(record["created_at"]) or datetime.now(),
        updated_at=_deserialize_datetime(record["updated_at"]) or datetime.now(),
        gate=DecisionGate(
            phase=DFNPhase(record["gate_phase"]),
            status=GateStatus(record["gate_status"]),
            feedback=record["gate_feedback"],
            decided_at=_deserialize_datetime(record["gate_decided_at"]),
        ),
    )


def _smart_brief_from_record(record: dict[str, Any] | None) -> SmartProductBrief | None:
    if not record:
        return None
    modules = [
        _module_from_record(item)
        for item in record.get("modules", [])
    ]
    return SmartProductBrief(
        category=record.get("category", ""),
        price_point=record.get("price_point", ""),
        consumer_profile=record.get("consumer_profile", ""),
        geo_market=record.get("geo_market", ""),
        competitive_set=list(record.get("competitive_set", [])),
        brand_guardrails=record.get("brand_guardrails", ""),
        constraints=record.get("constraints", ""),
        launch_season=record.get("launch_season", ""),
        uploaded_docs=list(record.get("uploaded_docs", [])),
        open_context=record.get("open_context", ""),
        modules=modules,
        generated_summary=record.get("generated_summary", ""),
        version=int(record.get("version", 1)),
        updated_at=_deserialize_datetime(record.get("updated_at")) or datetime.now(),
    )


def _module_from_record(item: dict[str, Any]) -> SmartBriefModule:
    revisions = [
        SmartBriefRevision(
            version=int(revision.get("version", 1)),
            content=revision.get("content", ""),
            updated_at=_deserialize_datetime(revision.get("updated_at")) or datetime.now(),
            updated_by=revision.get("updated_by", "system"),
            citations=list(revision.get("citations", [])),
        )
        for revision in item.get("revisions", [])
    ]
    return SmartBriefModule(
        key=item["key"],
        title=item["title"],
        content=item["content"],
        citations=list(item.get("citations", [])),
        version=int(item.get("version", 1)),
        updated_at=_deserialize_datetime(item.get("updated_at")) or datetime.now(),
        updated_by=item.get("updated_by", "system"),
        revisions=revisions,
    )


def _compliance_from_record(record: dict[str, Any] | None) -> ComplianceProfile:
    if not record:
        return ComplianceProfile()
    return ComplianceProfile(
        status=ComplianceStatus(record.get("status", ComplianceStatus.TRACKED.value)),
        data_classification=record.get("data_classification", "CONFIDENTIAL"),
        soc2_controls=list(record.get("soc2_controls", [])) or ComplianceProfile().soc2_controls,
        notes=record.get("notes", ComplianceProfile().notes),
    )


def _message_to_record(message: Message) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "sender": message.sender,
        "receiver": message.receiver,
        "message_type": message.message_type.value,
        "payload": json.dumps(message.payload),
        "project_id": message.project_id,
        "phase": message.phase.value,
        "step": message.step,
        "timestamp": _serialize_datetime(message.timestamp),
    }


def _message_from_record(row: sqlite3.Row | dict[str, Any]) -> Message:
    record = dict(row)
    return Message(
        sender=record["sender"],
        receiver=record["receiver"],
        message_type=MessageType(record["message_type"]),
        payload=json.loads(record["payload"]),
        project_id=record["project_id"],
        phase=DFNPhase(record["phase"]),
        step=record["step"],
        timestamp=_deserialize_datetime(record["timestamp"]) or datetime.now(),
        message_id=record["message_id"],
    )


def _output_to_record(output: AgentOutput) -> dict[str, Any]:
    return {
        "output_id": output.output_id,
        "agent_id": output.agent_id,
        "output_type": output.output_type,
        "data": json.dumps(output.data),
        "confidence_score": output.confidence_score,
        "sources": json.dumps(output.sources),
        "project_id": output.project_id,
        "tenant_id": output.tenant_id,
        "compliance_status": output.compliance_status.value,
        "data_classification": output.data_classification,
        "version": output.version,
        "timestamp": _serialize_datetime(output.timestamp),
    }


def _output_from_record(row: sqlite3.Row | dict[str, Any]) -> AgentOutput:
    record = dict(row)
    return AgentOutput(
        agent_id=record["agent_id"],
        output_type=record["output_type"],
        data=json.loads(record["data"]),
        confidence_score=record["confidence_score"],
        sources=json.loads(record["sources"]),
        project_id=record["project_id"],
        tenant_id=record.get("tenant_id", "preview"),
        compliance_status=ComplianceStatus(record.get("compliance_status", ComplianceStatus.TRACKED.value)),
        data_classification=record.get("data_classification", "CONFIDENTIAL"),
        version=record["version"],
        timestamp=_deserialize_datetime(record["timestamp"]) or datetime.now(),
        output_id=record["output_id"],
    )


def dataclass_to_api_dict(value: Any) -> Any:
    if isinstance(value, list):
        return [dataclass_to_api_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: dataclass_to_api_dict(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return dataclass_to_api_dict(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _run_to_record(run: ExecutionRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "project_id": run.project_id,
        "phase": run.phase.value,
        "status": run.status.value,
        "triggered_by": run.triggered_by,
        "summary": run.summary,
        "created_at": _serialize_datetime(run.created_at),
        "completed_at": _serialize_datetime(run.completed_at),
    }


def _run_from_record(row: sqlite3.Row | dict[str, Any]) -> ExecutionRun:
    record = dict(row)
    return ExecutionRun(
        run_id=record["run_id"],
        project_id=record["project_id"],
        phase=DFNPhase(record["phase"]),
        status=RunStatus(record["status"]),
        triggered_by=record["triggered_by"],
        summary=record["summary"],
        created_at=_deserialize_datetime(record["created_at"]) or datetime.now(),
        completed_at=_deserialize_datetime(record["completed_at"]),
    )


def _job_to_record(job: Job) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "project_id": job.project_id,
        "phase": job.phase.value,
        "status": job.status.value,
        "requested_by": job.requested_by,
        "tenant_id": job.tenant_id,
        "compliance_status": job.compliance_status.value,
        "data_classification": job.data_classification,
        "job_type": job.job_type,
        "created_at": _serialize_datetime(job.created_at),
        "updated_at": _serialize_datetime(job.updated_at),
        "error": job.error,
    }


def _job_from_record(row: sqlite3.Row | dict[str, Any]) -> Job:
    record = dict(row)
    return Job(
        job_id=record["job_id"],
        project_id=record["project_id"],
        phase=DFNPhase(record["phase"]),
        status=JobStatus(record["status"]),
        requested_by=record["requested_by"],
        tenant_id=record.get("tenant_id", "preview"),
        compliance_status=ComplianceStatus(record.get("compliance_status", ComplianceStatus.TRACKED.value)),
        data_classification=record.get("data_classification", "CONFIDENTIAL"),
        job_type=record["job_type"],
        created_at=_deserialize_datetime(record["created_at"]) or datetime.now(),
        updated_at=_deserialize_datetime(record["updated_at"]) or datetime.now(),
        error=record["error"],
    )


def _event_to_record(event: EventLog) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "project_id": event.project_id,
        "event_type": event.event_type,
        "level": event.level,
        "message": event.message,
        "tenant_id": event.tenant_id,
        "compliance_status": event.compliance_status.value,
        "data_classification": event.data_classification,
        "timestamp": _serialize_datetime(event.timestamp),
        "job_id": event.job_id,
        "run_id": event.run_id,
        "data": json.dumps(event.data),
    }


def _event_from_record(row: sqlite3.Row | dict[str, Any]) -> EventLog:
    record = dict(row)
    return EventLog(
        event_id=record["event_id"],
        project_id=record["project_id"],
        event_type=record["event_type"],
        level=record["level"],
        message=record["message"],
        tenant_id=record.get("tenant_id", "preview"),
        compliance_status=ComplianceStatus(record.get("compliance_status", ComplianceStatus.TRACKED.value)),
        data_classification=record.get("data_classification", "CONFIDENTIAL"),
        timestamp=_deserialize_datetime(record["timestamp"]) or datetime.now(),
        job_id=record["job_id"],
        run_id=record["run_id"],
        data=json.loads(record["data"]),
    )


def _user_to_record(user: User) -> dict[str, Any]:
    return {
        "user_id": user.user_id,
        "email": user.email,
        "password_hash": user.password_hash,
        "role": user.role.value,
        "created_at": _serialize_datetime(user.created_at),
    }


def _user_from_record(row: sqlite3.Row | dict[str, Any]) -> User:
    record = dict(row)
    return User(
        user_id=record["user_id"],
        email=record["email"],
        password_hash=record["password_hash"],
        role=UserRole(record["role"]),
        created_at=_deserialize_datetime(record["created_at"]) or datetime.now(),
    )


def _session_to_record(session: Session) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "token": session.token,
        "created_at": _serialize_datetime(session.created_at),
    }


def _session_from_record(row: sqlite3.Row | dict[str, Any]) -> Session:
    record = dict(row)
    return Session(
        session_id=record["session_id"],
        user_id=record["user_id"],
        token=record["token"],
        created_at=_deserialize_datetime(record["created_at"]) or datetime.now(),
    )


def _collaborator_to_record(collaborator: ProjectCollaborator) -> dict[str, Any]:
    return {
        "collaborator_id": collaborator.collaborator_id,
        "project_id": collaborator.project_id,
        "user_id": collaborator.user_id,
        "access_role": collaborator.access_role.value,
        "created_at": _serialize_datetime(collaborator.created_at),
    }


def _collaborator_from_record(row: sqlite3.Row | dict[str, Any]) -> ProjectCollaborator:
    record = dict(row)
    return ProjectCollaborator(
        collaborator_id=record["collaborator_id"],
        project_id=record["project_id"],
        user_id=record["user_id"],
        access_role=ProjectAccessRole(record["access_role"]),
        created_at=_deserialize_datetime(record["created_at"]) or datetime.now(),
    )


def _invitation_to_record(invitation: ProjectInvitation) -> dict[str, Any]:
    return {
        "invitation_id": invitation.invitation_id,
        "project_id": invitation.project_id,
        "invited_email": invitation.invited_email,
        "access_role": invitation.access_role.value,
        "invited_by_user_id": invitation.invited_by_user_id,
        "token": invitation.token,
        "status": invitation.status.value,
        "created_at": _serialize_datetime(invitation.created_at),
    }


def _invitation_from_record(row: sqlite3.Row | dict[str, Any]) -> ProjectInvitation:
    record = dict(row)
    return ProjectInvitation(
        invitation_id=record["invitation_id"],
        project_id=record["project_id"],
        invited_email=record["invited_email"],
        access_role=ProjectAccessRole(record["access_role"]),
        invited_by_user_id=record["invited_by_user_id"],
        token=record["token"],
        status=InvitationStatus(record["status"]),
        created_at=_deserialize_datetime(record["created_at"]) or datetime.now(),
    )


class ContextStore(ABC):
    @abstractmethod
    def create_project(self, project: Project) -> Project:
        raise NotImplementedError

    @abstractmethod
    def get_project(self, project_id: str) -> Project:
        raise NotImplementedError

    @abstractmethod
    def list_projects(self, owner_user_id: str | None = None) -> list[Project]:
        raise NotImplementedError

    @abstractmethod
    def save_project(self, project: Project) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_message(self, message: Message) -> Message:
        raise NotImplementedError

    @abstractmethod
    def list_messages(self, project_id: str) -> list[Message]:
        raise NotImplementedError

    @abstractmethod
    def add_output(self, output: AgentOutput) -> AgentOutput:
        raise NotImplementedError

    @abstractmethod
    def list_outputs(self, project_id: str) -> list[AgentOutput]:
        raise NotImplementedError

    @abstractmethod
    def add_run(self, run: ExecutionRun) -> ExecutionRun:
        raise NotImplementedError

    @abstractmethod
    def save_run(self, run: ExecutionRun) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_runs(self, project_id: str) -> list[ExecutionRun]:
        raise NotImplementedError

    @abstractmethod
    def add_job(self, job: Job) -> Job:
        raise NotImplementedError

    @abstractmethod
    def get_job(self, job_id: str) -> Job:
        raise NotImplementedError

    @abstractmethod
    def save_job(self, job: Job) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_jobs(self, project_id: str | None = None) -> list[Job]:
        raise NotImplementedError

    @abstractmethod
    def add_event(self, event: EventLog) -> EventLog:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, project_id: str) -> list[EventLog]:
        raise NotImplementedError

    @abstractmethod
    def create_user(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    def get_user(self, user_id: str) -> User:
        raise NotImplementedError

    @abstractmethod
    def get_user_by_email(self, email: str) -> User:
        raise NotImplementedError

    @abstractmethod
    def list_users(self) -> list[User]:
        raise NotImplementedError

    @abstractmethod
    def create_session(self, session: Session) -> Session:
        raise NotImplementedError

    @abstractmethod
    def get_session_by_token(self, token: str) -> Session:
        raise NotImplementedError

    @abstractmethod
    def delete_session(self, token: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_collaborator(self, collaborator: ProjectCollaborator) -> ProjectCollaborator:
        raise NotImplementedError

    @abstractmethod
    def get_collaborator(self, project_id: str, user_id: str) -> ProjectCollaborator:
        raise NotImplementedError

    @abstractmethod
    def list_collaborators(self, project_id: str) -> list[ProjectCollaborator]:
        raise NotImplementedError

    @abstractmethod
    def add_invitation(self, invitation: ProjectInvitation) -> ProjectInvitation:
        raise NotImplementedError

    @abstractmethod
    def get_invitation_by_token(self, token: str) -> ProjectInvitation:
        raise NotImplementedError

    @abstractmethod
    def save_invitation(self, invitation: ProjectInvitation) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_invitations(self, project_id: str) -> list[ProjectInvitation]:
        raise NotImplementedError


class InMemoryContextStore(ContextStore):
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}
        self.messages: dict[str, list[Message]] = defaultdict(list)
        self.outputs: dict[str, list[AgentOutput]] = defaultdict(list)
        self.runs: dict[str, list[ExecutionRun]] = defaultdict(list)
        self.jobs: dict[str, Job] = {}
        self.events: dict[str, list[EventLog]] = defaultdict(list)
        self.users: dict[str, User] = {}
        self.sessions: dict[str, Session] = {}
        self.collaborators: dict[str, list[ProjectCollaborator]] = defaultdict(list)
        self.invitations: dict[str, ProjectInvitation] = {}

    def create_project(self, project: Project) -> Project:
        self.projects[project.project_id] = project
        return project

    def get_project(self, project_id: str) -> Project:
        return self.projects[project_id]

    def list_projects(self, owner_user_id: str | None = None) -> list[Project]:
        projects = list(self.projects.values())
        if owner_user_id is not None:
            collaborator_project_ids = {
                collaborator.project_id
                for collaborator_group in self.collaborators.values()
                for collaborator in collaborator_group
                if collaborator.user_id == owner_user_id
            }
            projects = [
                project
                for project in projects
                if project.owner_user_id == owner_user_id or project.project_id in collaborator_project_ids
            ]
        return sorted(projects, key=lambda project: project.created_at)

    def save_project(self, project: Project) -> None:
        project.touch()
        self.projects[project.project_id] = project

    def add_message(self, message: Message) -> Message:
        self.messages[message.project_id].append(message)
        return message

    def list_messages(self, project_id: str) -> list[Message]:
        return list(self.messages[project_id])

    def add_output(self, output: AgentOutput) -> AgentOutput:
        history = self.outputs[output.project_id]
        output.version = len(history) + 1
        history.append(output)
        return output

    def list_outputs(self, project_id: str) -> list[AgentOutput]:
        return list(self.outputs[project_id])

    def add_run(self, run: ExecutionRun) -> ExecutionRun:
        self.runs[run.project_id].append(run)
        return run

    def save_run(self, run: ExecutionRun) -> None:
        runs = self.runs[run.project_id]
        for index, existing in enumerate(runs):
            if existing.run_id == run.run_id:
                runs[index] = run
                return
        runs.append(run)

    def list_runs(self, project_id: str) -> list[ExecutionRun]:
        return list(self.runs[project_id])

    def add_job(self, job: Job) -> Job:
        self.jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> Job:
        return self.jobs[job_id]

    def save_job(self, job: Job) -> None:
        job.touch()
        self.jobs[job.job_id] = job

    def list_jobs(self, project_id: str | None = None) -> list[Job]:
        jobs = list(self.jobs.values())
        if project_id is not None:
            jobs = [job for job in jobs if job.project_id == project_id]
        return sorted(jobs, key=lambda job: job.created_at)

    def add_event(self, event: EventLog) -> EventLog:
        self.events[event.project_id].append(event)
        return event

    def list_events(self, project_id: str) -> list[EventLog]:
        return list(self.events[project_id])

    def create_user(self, user: User) -> User:
        self.users[user.user_id] = user
        return user

    def get_user(self, user_id: str) -> User:
        return self.users[user_id]

    def get_user_by_email(self, email: str) -> User:
        for user in self.users.values():
            if user.email == email:
                return user
        raise KeyError(email)

    def list_users(self) -> list[User]:
        return sorted(self.users.values(), key=lambda user: user.created_at)

    def create_session(self, session: Session) -> Session:
        self.sessions[session.token] = session
        return session

    def get_session_by_token(self, token: str) -> Session:
        return self.sessions[token]

    def delete_session(self, token: str) -> None:
        self.sessions.pop(token, None)

    def add_collaborator(self, collaborator: ProjectCollaborator) -> ProjectCollaborator:
        existing = self.collaborators[collaborator.project_id]
        for index, item in enumerate(existing):
            if item.user_id == collaborator.user_id:
                existing[index] = collaborator
                return collaborator
        existing.append(collaborator)
        return collaborator

    def get_collaborator(self, project_id: str, user_id: str) -> ProjectCollaborator:
        for collaborator in self.collaborators[project_id]:
            if collaborator.user_id == user_id:
                return collaborator
        raise KeyError((project_id, user_id))

    def list_collaborators(self, project_id: str) -> list[ProjectCollaborator]:
        return list(self.collaborators[project_id])

    def add_invitation(self, invitation: ProjectInvitation) -> ProjectInvitation:
        self.invitations[invitation.token] = invitation
        return invitation

    def get_invitation_by_token(self, token: str) -> ProjectInvitation:
        return self.invitations[token]

    def save_invitation(self, invitation: ProjectInvitation) -> None:
        self.invitations[invitation.token] = invitation

    def list_invitations(self, project_id: str) -> list[ProjectInvitation]:
        return [invitation for invitation in self.invitations.values() if invitation.project_id == project_id]


class SQLiteContextStore(ContextStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    brief TEXT NOT NULL,
                    owner_user_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'preview',
                    smart_brief TEXT,
                    compliance TEXT NOT NULL DEFAULT '{}',
                    current_phase TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    gate_phase TEXT NOT NULL,
                    gate_status TEXT NOT NULL,
                    gate_feedback TEXT,
                    gate_decided_at TEXT
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    receiver TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    step TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS outputs (
                    output_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    output_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    sources TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'preview',
                    compliance_status TEXT NOT NULL DEFAULT 'TRACKED',
                    data_classification TEXT NOT NULL DEFAULT 'CONFIDENTIAL',
                    version INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS execution_runs (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    status TEXT NOT NULL,
                    triggered_by TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'preview',
                    compliance_status TEXT NOT NULL DEFAULT 'TRACKED',
                    data_classification TEXT NOT NULL DEFAULT 'CONFIDENTIAL',
                    job_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error TEXT
                );

                CREATE TABLE IF NOT EXISTS event_logs (
                    event_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'preview',
                    compliance_status TEXT NOT NULL DEFAULT 'TRACKED',
                    data_classification TEXT NOT NULL DEFAULT 'CONFIDENTIAL',
                    timestamp TEXT NOT NULL,
                    job_id TEXT,
                    run_id TEXT,
                    data TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'MEMBER',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS project_collaborators (
                    collaborator_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    access_role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(project_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS project_invitations (
                    invitation_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    invited_email TEXT NOT NULL,
                    access_role TEXT NOT NULL,
                    invited_by_user_id TEXT NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(projects)").fetchall()}
            if "owner_user_id" not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN owner_user_id TEXT NOT NULL DEFAULT 'legacy-demo-user'")
            if "tenant_id" not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'preview'")
            if "smart_brief" not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN smart_brief TEXT")
            if "compliance" not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN compliance TEXT NOT NULL DEFAULT '{}'")
            user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "role" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'MEMBER'")
            output_columns = {row["name"] for row in conn.execute("PRAGMA table_info(outputs)").fetchall()}
            if "tenant_id" not in output_columns:
                conn.execute("ALTER TABLE outputs ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'preview'")
            if "compliance_status" not in output_columns:
                conn.execute("ALTER TABLE outputs ADD COLUMN compliance_status TEXT NOT NULL DEFAULT 'TRACKED'")
            if "data_classification" not in output_columns:
                conn.execute("ALTER TABLE outputs ADD COLUMN data_classification TEXT NOT NULL DEFAULT 'CONFIDENTIAL'")
            job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
            if "tenant_id" not in job_columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'preview'")
            if "compliance_status" not in job_columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN compliance_status TEXT NOT NULL DEFAULT 'TRACKED'")
            if "data_classification" not in job_columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN data_classification TEXT NOT NULL DEFAULT 'CONFIDENTIAL'")
            event_columns = {row["name"] for row in conn.execute("PRAGMA table_info(event_logs)").fetchall()}
            if "tenant_id" not in event_columns:
                conn.execute("ALTER TABLE event_logs ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'preview'")
            if "compliance_status" not in event_columns:
                conn.execute("ALTER TABLE event_logs ADD COLUMN compliance_status TEXT NOT NULL DEFAULT 'TRACKED'")
            if "data_classification" not in event_columns:
                conn.execute("ALTER TABLE event_logs ADD COLUMN data_classification TEXT NOT NULL DEFAULT 'CONFIDENTIAL'")

    def create_project(self, project: Project) -> Project:
        record = _project_to_record(project)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    project_id, name, brief, owner_user_id, tenant_id, smart_brief, compliance, current_phase, status, created_at, updated_at,
                    gate_phase, gate_status, gate_feedback, gate_decided_at
                ) VALUES (
                    :project_id, :name, :brief, :owner_user_id, :tenant_id, :smart_brief, :compliance, :current_phase, :status, :created_at, :updated_at,
                    :gate_phase, :gate_status, :gate_feedback, :gate_decided_at
                )
                """,
                record,
            )
        return project

    def get_project(self, project_id: str) -> Project:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        if row is None:
            raise KeyError(project_id)
        return _project_from_record(row)

    def list_projects(self, owner_user_id: str | None = None) -> list[Project]:
        with self._connect() as conn:
            if owner_user_id is None:
                rows = conn.execute("SELECT * FROM projects ORDER BY created_at ASC").fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT DISTINCT projects.*
                    FROM projects
                    LEFT JOIN project_collaborators ON project_collaborators.project_id = projects.project_id
                    WHERE projects.owner_user_id = ? OR project_collaborators.user_id = ?
                    ORDER BY projects.created_at ASC
                    """,
                    (owner_user_id, owner_user_id),
                ).fetchall()
        return [_project_from_record(row) for row in rows]

    def save_project(self, project: Project) -> None:
        project.touch()
        record = _project_to_record(project)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE projects
                SET name = :name,
                    brief = :brief,
                    owner_user_id = :owner_user_id,
                    tenant_id = :tenant_id,
                    smart_brief = :smart_brief,
                    compliance = :compliance,
                    current_phase = :current_phase,
                    status = :status,
                    created_at = :created_at,
                    updated_at = :updated_at,
                    gate_phase = :gate_phase,
                    gate_status = :gate_status,
                    gate_feedback = :gate_feedback,
                    gate_decided_at = :gate_decided_at
                WHERE project_id = :project_id
                """,
                record,
            )

    def add_message(self, message: Message) -> Message:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    message_id, project_id, sender, receiver, message_type, payload, phase, step, timestamp
                ) VALUES (
                    :message_id, :project_id, :sender, :receiver, :message_type, :payload, :phase, :step, :timestamp
                )
                """,
                _message_to_record(message),
            )
        return message

    def list_messages(self, project_id: str) -> list[Message]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE project_id = ? ORDER BY timestamp ASC",
                (project_id,),
            ).fetchall()
        return [_message_from_record(row) for row in rows]

    def add_output(self, output: AgentOutput) -> AgentOutput:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS max_version FROM outputs WHERE project_id = ?",
                (output.project_id,),
            ).fetchone()
            output.version = int(row["max_version"]) + 1
            conn.execute(
                """
                INSERT INTO outputs (
                    output_id, project_id, agent_id, output_type, data, confidence_score, sources, tenant_id, compliance_status, data_classification, version, timestamp
                ) VALUES (
                    :output_id, :project_id, :agent_id, :output_type, :data, :confidence_score, :sources, :tenant_id, :compliance_status, :data_classification, :version, :timestamp
                )
                """,
                _output_to_record(output),
            )
        return output

    def list_outputs(self, project_id: str) -> list[AgentOutput]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM outputs WHERE project_id = ? ORDER BY version ASC",
                (project_id,),
            ).fetchall()
        return [_output_from_record(row) for row in rows]

    def add_run(self, run: ExecutionRun) -> ExecutionRun:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO execution_runs (
                    run_id, project_id, phase, status, triggered_by, summary, created_at, completed_at
                ) VALUES (
                    :run_id, :project_id, :phase, :status, :triggered_by, :summary, :created_at, :completed_at
                )
                """,
                _run_to_record(run),
            )
        return run

    def save_run(self, run: ExecutionRun) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE execution_runs
                SET phase = :phase,
                    status = :status,
                    triggered_by = :triggered_by,
                    summary = :summary,
                    created_at = :created_at,
                    completed_at = :completed_at
                WHERE run_id = :run_id
                """,
                _run_to_record(run),
            )

    def list_runs(self, project_id: str) -> list[ExecutionRun]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM execution_runs WHERE project_id = ? ORDER BY created_at ASC",
                (project_id,),
            ).fetchall()
        return [_run_from_record(row) for row in rows]

    def add_job(self, job: Job) -> Job:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, project_id, phase, status, requested_by, tenant_id, compliance_status, data_classification, job_type, created_at, updated_at, error
                ) VALUES (
                    :job_id, :project_id, :phase, :status, :requested_by, :tenant_id, :compliance_status, :data_classification, :job_type, :created_at, :updated_at, :error
                )
                """,
                _job_to_record(job),
            )
        return job

    def get_job(self, job_id: str) -> Job:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return _job_from_record(row)

    def save_job(self, job: Job) -> None:
        job.touch()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET project_id = :project_id,
                    phase = :phase,
                    status = :status,
                    requested_by = :requested_by,
                    tenant_id = :tenant_id,
                    compliance_status = :compliance_status,
                    data_classification = :data_classification,
                    job_type = :job_type,
                    created_at = :created_at,
                    updated_at = :updated_at,
                    error = :error
                WHERE job_id = :job_id
                """,
                _job_to_record(job),
            )

    def list_jobs(self, project_id: str | None = None) -> list[Job]:
        with self._connect() as conn:
            if project_id is None:
                rows = conn.execute("SELECT * FROM jobs ORDER BY created_at ASC").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at ASC",
                    (project_id,),
                ).fetchall()
        return [_job_from_record(row) for row in rows]

    def add_event(self, event: EventLog) -> EventLog:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO event_logs (
                    event_id, project_id, event_type, level, message, tenant_id, compliance_status, data_classification, timestamp, job_id, run_id, data
                ) VALUES (
                    :event_id, :project_id, :event_type, :level, :message, :tenant_id, :compliance_status, :data_classification, :timestamp, :job_id, :run_id, :data
                )
                """,
                _event_to_record(event),
            )
        return event

    def list_events(self, project_id: str) -> list[EventLog]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM event_logs WHERE project_id = ? ORDER BY timestamp ASC",
                (project_id,),
            ).fetchall()
        return [_event_from_record(row) for row in rows]

    def create_user(self, user: User) -> User:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, email, password_hash, role, created_at)
                VALUES (:user_id, :email, :password_hash, :role, :created_at)
                """,
                _user_to_record(user),
            )
        return user

    def get_user(self, user_id: str) -> User:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            raise KeyError(user_id)
        return _user_from_record(row)

    def get_user_by_email(self, email: str) -> User:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            raise KeyError(email)
        return _user_from_record(row)

    def list_users(self) -> list[User]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at ASC").fetchall()
        return [_user_from_record(row) for row in rows]

    def create_session(self, session: Session) -> Session:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_id, token, created_at)
                VALUES (:session_id, :user_id, :token, :created_at)
                """,
                _session_to_record(session),
            )
        return session

    def get_session_by_token(self, token: str) -> Session:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
        if row is None:
            raise KeyError(token)
        return _session_from_record(row)

    def delete_session(self, token: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def add_collaborator(self, collaborator: ProjectCollaborator) -> ProjectCollaborator:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO project_collaborators (collaborator_id, project_id, user_id, access_role, created_at)
                VALUES (:collaborator_id, :project_id, :user_id, :access_role, :created_at)
                ON CONFLICT(project_id, user_id) DO UPDATE SET
                    access_role = excluded.access_role,
                    created_at = excluded.created_at
                """,
                _collaborator_to_record(collaborator),
            )
        return collaborator

    def get_collaborator(self, project_id: str, user_id: str) -> ProjectCollaborator:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM project_collaborators WHERE project_id = ? AND user_id = ?",
                (project_id, user_id),
            ).fetchone()
        if row is None:
            raise KeyError((project_id, user_id))
        return _collaborator_from_record(row)

    def list_collaborators(self, project_id: str) -> list[ProjectCollaborator]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM project_collaborators WHERE project_id = ? ORDER BY created_at ASC",
                (project_id,),
            ).fetchall()
        return [_collaborator_from_record(row) for row in rows]

    def add_invitation(self, invitation: ProjectInvitation) -> ProjectInvitation:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO project_invitations (
                    invitation_id, project_id, invited_email, access_role, invited_by_user_id, token, status, created_at
                ) VALUES (
                    :invitation_id, :project_id, :invited_email, :access_role, :invited_by_user_id, :token, :status, :created_at
                )
                """,
                _invitation_to_record(invitation),
            )
        return invitation

    def get_invitation_by_token(self, token: str) -> ProjectInvitation:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM project_invitations WHERE token = ?", (token,)).fetchone()
        if row is None:
            raise KeyError(token)
        return _invitation_from_record(row)

    def save_invitation(self, invitation: ProjectInvitation) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE project_invitations
                SET project_id = :project_id,
                    invited_email = :invited_email,
                    access_role = :access_role,
                    invited_by_user_id = :invited_by_user_id,
                    token = :token,
                    status = :status,
                    created_at = :created_at
                WHERE invitation_id = :invitation_id
                """,
                _invitation_to_record(invitation),
            )

    def list_invitations(self, project_id: str) -> list[ProjectInvitation]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM project_invitations WHERE project_id = ? ORDER BY created_at ASC",
                (project_id,),
            ).fetchall()
        return [_invitation_from_record(row) for row in rows]
