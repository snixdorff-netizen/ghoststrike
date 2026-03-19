from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DFNPhase(str, Enum):
    EMPATHIZE = "EMPATHIZE"
    IDEATE = "IDEATE"
    EVALUATE = "EVALUATE"
    REALIZE = "REALIZE"
    MEASURE = "MEASURE"


class MessageType(str, Enum):
    WORK_ORDER = "WORK_ORDER"
    RESULT = "RESULT"
    STATUS_UPDATE = "STATUS_UPDATE"
    HUMAN_GATE_REQUEST = "HUMAN_GATE_REQUEST"
    HUMAN_GATE_RESPONSE = "HUMAN_GATE_RESPONSE"
    ERROR = "ERROR"
    FEEDBACK_LOOP = "FEEDBACK_LOOP"


class ProjectStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_GATE = "WAITING_FOR_GATE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GateStatus(str, Enum):
    NOT_OPEN = "NOT_OPEN"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RunStatus(str, Enum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class ProjectAccessRole(str, Enum):
    VIEWER = "VIEWER"
    EDITOR = "EDITOR"


class InvitationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"


class ComplianceStatus(str, Enum):
    TRACKED = "TRACKED"
    IN_REVIEW = "IN_REVIEW"
    READY = "READY"


@dataclass(slots=True, frozen=True)
class AgentSpec:
    agent_id: str
    code_name: str
    display_name: str
    phase: DFNPhase
    description: str


@dataclass(slots=True)
class Message:
    sender: str
    receiver: str
    message_type: MessageType
    payload: dict[str, Any]
    project_id: str
    phase: DFNPhase
    step: str
    timestamp: datetime = field(default_factory=utcnow)
    message_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class AgentOutput:
    agent_id: str
    output_type: str
    data: dict[str, Any]
    confidence_score: float
    sources: list[str]
    project_id: str
    tenant_id: str = "preview"
    compliance_status: ComplianceStatus = ComplianceStatus.TRACKED
    data_classification: str = "CONFIDENTIAL"
    version: int = 1
    timestamp: datetime = field(default_factory=utcnow)
    output_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class DecisionGate:
    phase: DFNPhase
    status: GateStatus = GateStatus.NOT_OPEN
    feedback: str | None = None
    decided_at: datetime | None = None


@dataclass(slots=True)
class SmartBriefRevision:
    version: int
    content: str
    updated_at: datetime = field(default_factory=utcnow)
    updated_by: str = "system"
    citations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SmartBriefModule:
    key: str
    title: str
    content: str
    citations: list[str] = field(default_factory=list)
    version: int = 1
    updated_at: datetime = field(default_factory=utcnow)
    updated_by: str = "system"
    revisions: list[SmartBriefRevision] = field(default_factory=list)


@dataclass(slots=True)
class SmartProductBrief:
    category: str
    price_point: str
    consumer_profile: str
    geo_market: str
    competitive_set: list[str] = field(default_factory=list)
    brand_guardrails: str = ""
    constraints: str = ""
    launch_season: str = ""
    uploaded_docs: list[str] = field(default_factory=list)
    open_context: str = ""
    modules: list[SmartBriefModule] = field(default_factory=list)
    generated_summary: str = ""
    version: int = 1
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ComplianceProfile:
    status: ComplianceStatus = ComplianceStatus.TRACKED
    data_classification: str = "CONFIDENTIAL"
    soc2_controls: list[str] = field(
        default_factory=lambda: [
            "access_control",
            "audit_logging",
            "tenant_isolation",
            "change_management",
            "data_retention",
        ]
    )
    notes: str = "Preview workspace tracked for multi-tenant and SOC 2 readiness."


@dataclass(slots=True)
class Project:
    name: str
    brief: str
    owner_user_id: str = "system"
    tenant_id: str = "preview"
    smart_brief: SmartProductBrief | None = None
    compliance: ComplianceProfile = field(default_factory=ComplianceProfile)
    project_id: str = field(default_factory=lambda: str(uuid4()))
    current_phase: DFNPhase = DFNPhase.EMPATHIZE
    status: ProjectStatus = ProjectStatus.DRAFT
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    gate: DecisionGate = field(default_factory=lambda: DecisionGate(phase=DFNPhase.EMPATHIZE))

    def touch(self) -> None:
        self.updated_at = utcnow()


@dataclass(slots=True)
class ExecutionRun:
    project_id: str
    phase: DFNPhase
    status: RunStatus
    triggered_by: str
    summary: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None


@dataclass(slots=True)
class Job:
    project_id: str
    phase: DFNPhase
    status: JobStatus
    requested_by: str
    tenant_id: str = "preview"
    compliance_status: ComplianceStatus = ComplianceStatus.TRACKED
    data_classification: str = "CONFIDENTIAL"
    job_type: str = "phase_execution"
    job_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    error: str | None = None

    def touch(self) -> None:
        self.updated_at = utcnow()


@dataclass(slots=True)
class EventLog:
    project_id: str
    event_type: str
    level: str
    message: str
    tenant_id: str = "preview"
    compliance_status: ComplianceStatus = ComplianceStatus.TRACKED
    data_classification: str = "CONFIDENTIAL"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utcnow)
    job_id: str | None = None
    run_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class User:
    email: str
    password_hash: str
    role: UserRole = UserRole.MEMBER
    user_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class Session:
    user_id: str
    token: str
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ProjectCollaborator:
    project_id: str
    user_id: str
    access_role: ProjectAccessRole
    collaborator_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ProjectInvitation:
    project_id: str
    invited_email: str
    access_role: ProjectAccessRole
    invited_by_user_id: str
    token: str
    status: InvitationStatus = InvitationStatus.PENDING
    invitation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utcnow)
