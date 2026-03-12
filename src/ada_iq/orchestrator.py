from __future__ import annotations

from ada_iq.auth import hash_password, new_session_token, verify_password
from ada_iq.agents import PHASE_TO_AGENTS, StubAgentRunner
from ada_iq.models import (
    DFNPhase,
    ExecutionRun,
    GateStatus,
    Message,
    MessageType,
    Project,
    ProjectAccessRole,
    ProjectCollaborator,
    ProjectInvitation,
    ProjectStatus,
    RunStatus,
    Session,
    User,
    UserRole,
    InvitationStatus,
)
from ada_iq.observability import EventLogger
from ada_iq.queue import InProcessJobQueue
from ada_iq.store import ContextStore, dataclass_to_api_dict


PHASE_ORDER: tuple[DFNPhase, ...] = (
    DFNPhase.EMPATHIZE,
    DFNPhase.IDEATE,
    DFNPhase.EVALUATE,
    DFNPhase.REALIZE,
    DFNPhase.MEASURE,
)


class Orchestrator:
    def __init__(
        self,
        store: ContextStore,
        runner: StubAgentRunner | None = None,
        logger: EventLogger | None = None,
        queue: InProcessJobQueue | None = None,
    ) -> None:
        self.store = store
        self.runner = runner or StubAgentRunner()
        self.logger = logger or EventLogger(store)
        self.queue = queue or InProcessJobQueue(store, self.logger)

    def register_user(self, email: str, password: str, role: UserRole | str = UserRole.MEMBER) -> dict:
        try:
            self.store.get_user_by_email(email)
            raise ValueError("User already exists.")
        except KeyError:
            pass
        if isinstance(role, str):
            role = UserRole(role)
        user = self.store.create_user(User(email=email, password_hash=hash_password(password), role=role))
        session = self.store.create_session(Session(user_id=user.user_id, token=new_session_token()))
        return {"user": dataclass_to_api_dict(user), "token": session.token}

    def login_user(self, email: str, password: str) -> dict:
        try:
            user = self.store.get_user_by_email(email)
        except KeyError as exc:
            raise ValueError("Invalid credentials.") from exc
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials.")
        session = self.store.create_session(Session(user_id=user.user_id, token=new_session_token()))
        return {"user": dataclass_to_api_dict(user), "token": session.token}

    def get_user_for_token(self, token: str) -> dict:
        session = self.store.get_session_by_token(token)
        return dataclass_to_api_dict(self.store.get_user(session.user_id))

    def logout_user(self, token: str) -> None:
        self.store.delete_session(token)

    def list_users(self, requester_user_id: str) -> list[dict]:
        requester = self.store.get_user(requester_user_id)
        if requester.role != UserRole.ADMIN:
            raise PermissionError("Admin access required.")
        return [dataclass_to_api_dict(user) for user in self.store.list_users()]

    def list_all_projects(self, requester_user_id: str) -> list[dict]:
        requester = self.store.get_user(requester_user_id)
        if requester.role != UserRole.ADMIN:
            raise PermissionError("Admin access required.")
        return self.list_projects_snapshot()

    def admin_create_user(self, requester_user_id: str, email: str, password: str, role: UserRole | str = UserRole.MEMBER) -> dict:
        requester = self.store.get_user(requester_user_id)
        if requester.role != UserRole.ADMIN:
            raise PermissionError("Admin access required.")
        created = self.register_user(email, password, role=role)
        self.logger.log(
            project_id="platform",
            event_type="admin_user_created",
            level="INFO",
            message=f"Admin created user {email}.",
            data={"actor": self._actor_label(requester_user_id), "email": email, "role": created["user"]["role"]},
        )
        return created

    def create_project(self, name: str, brief: str, owner_user_id: str = "system") -> Project:
        project = Project(name=name, brief=brief, owner_user_id=owner_user_id)
        return self.store.create_project(project)

    def _actor_label(self, user_id: str | None) -> str:
        if user_id is None:
            return "human_user"
        try:
            return self.store.get_user(user_id).email
        except KeyError:
            return user_id

    def add_project_collaborator(self, project_id: str, requester_user_id: str, collaborator_email: str, access_role: ProjectAccessRole | str) -> dict:
        project = self.store.get_project(project_id)
        if project.owner_user_id != requester_user_id:
            raise PermissionError("Only the project owner can manage collaborators.")
        collaborator_user = self.store.get_user_by_email(collaborator_email)
        if isinstance(access_role, str):
            access_role = ProjectAccessRole(access_role)
        collaborator = self.store.add_collaborator(
            ProjectCollaborator(project_id=project_id, user_id=collaborator_user.user_id, access_role=access_role)
        )
        self.logger.log(
            project_id,
            event_type="collaborator_added",
            level="INFO",
            message=f"Added collaborator {collaborator_user.email} as {access_role.value}.",
            data={"actor": self._actor_label(requester_user_id), "collaborator_email": collaborator_user.email, "access_role": access_role.value},
        )
        return dataclass_to_api_dict(collaborator)

    def invite_project_collaborator(self, project_id: str, requester_user_id: str, invited_email: str, access_role: ProjectAccessRole | str) -> dict:
        project = self.store.get_project(project_id)
        if project.owner_user_id != requester_user_id:
            raise PermissionError("Only the project owner can manage collaborators.")
        if isinstance(access_role, str):
            access_role = ProjectAccessRole(access_role)
        invitation = self.store.add_invitation(
            ProjectInvitation(
                project_id=project_id,
                invited_email=invited_email,
                access_role=access_role,
                invited_by_user_id=requester_user_id,
                token=new_session_token(),
            )
        )
        self.logger.log(
            project_id,
            event_type="invitation_created",
            level="INFO",
            message=f"Created invitation for {invited_email} as {access_role.value}.",
            data={"actor": self._actor_label(requester_user_id), "invited_email": invited_email, "access_role": access_role.value},
        )
        return dataclass_to_api_dict(invitation)

    def accept_invitation(self, token: str, user_id: str) -> dict:
        invitation = self.store.get_invitation_by_token(token)
        user = self.store.get_user(user_id)
        if invitation.invited_email != user.email:
            raise PermissionError("Invitation email does not match the authenticated user.")
        if invitation.status != InvitationStatus.PENDING:
            raise ValueError("Invitation has already been used.")
        collaborator = self.store.add_collaborator(
            ProjectCollaborator(project_id=invitation.project_id, user_id=user_id, access_role=invitation.access_role)
        )
        invitation.status = InvitationStatus.ACCEPTED
        self.store.save_invitation(invitation)
        self.logger.log(
            invitation.project_id,
            event_type="invitation_accepted",
            level="INFO",
            message=f"Accepted invitation for {user.email}.",
            data={"actor": self._actor_label(user_id), "invited_email": user.email, "access_role": invitation.access_role.value},
        )
        return dataclass_to_api_dict(collaborator)

    def list_project_collaborators(self, project_id: str, requester_user_id: str) -> list[dict]:
        self._get_project_with_access(project_id, requester_user_id, require_write=False)
        return [dataclass_to_api_dict(collaborator) for collaborator in self.store.list_collaborators(project_id)]

    def list_project_invitations(self, project_id: str, requester_user_id: str) -> list[dict]:
        project = self.store.get_project(project_id)
        if project.owner_user_id != requester_user_id:
            raise PermissionError("Only the project owner can view invitations.")
        return [dataclass_to_api_dict(invitation) for invitation in self.store.list_invitations(project_id)]

    def submit_project_feedback(self, project_id: str, requester_user_id: str, summary: str, category: str = "GENERAL") -> dict:
        project = self._get_project_with_access(project_id, requester_user_id, require_write=False)
        event = self.logger.log(
            project.project_id,
            event_type="alpha_feedback",
            level="INFO",
            message=summary,
            data={"actor": self._actor_label(requester_user_id), "category": category},
        )
        return dataclass_to_api_dict(event)

    def list_project_feedback(self, project_id: str, requester_user_id: str) -> list[dict]:
        self._get_project_with_access(project_id, requester_user_id, require_write=False)
        return [
            dataclass_to_api_dict(event)
            for event in self.store.list_events(project_id)
            if event.event_type == "alpha_feedback"
        ]

    def _get_project_with_access(self, project_id: str, user_id: str, require_write: bool) -> Project:
        project = self.store.get_project(project_id)
        if project.owner_user_id == user_id:
            return project
        try:
            collaborator = self.store.get_collaborator(project_id, user_id)
        except KeyError as exc:
            raise PermissionError("Project access denied.") from exc
        if require_write and collaborator.access_role != ProjectAccessRole.EDITOR:
            raise PermissionError("Write access required.")
        return project

    def get_project_snapshot(self, project_id: str, owner_user_id: str | None = None) -> dict:
        project = self._get_project_with_access(project_id, owner_user_id, require_write=False) if owner_user_id is not None else self.store.get_project(project_id)
        return {
            "project": dataclass_to_api_dict(project),
            "messages": dataclass_to_api_dict(self.store.list_messages(project_id)),
            "outputs": dataclass_to_api_dict(self.store.list_outputs(project_id)),
            "runs": dataclass_to_api_dict(self.store.list_runs(project_id)),
            "jobs": dataclass_to_api_dict(self.store.list_jobs(project_id)),
            "events": dataclass_to_api_dict(self.store.list_events(project_id)),
            "feedback": self.list_project_feedback(project_id, owner_user_id) if owner_user_id is not None else [
                dataclass_to_api_dict(event) for event in self.store.list_events(project_id) if event.event_type == "alpha_feedback"
            ],
            "collaborators": dataclass_to_api_dict(self.store.list_collaborators(project_id)),
        }

    def list_projects_snapshot(self, owner_user_id: str | None = None) -> list[dict]:
        return [dataclass_to_api_dict(project) for project in self.store.list_projects(owner_user_id)]

    def export_project_snapshot(self, project_id: str, owner_user_id: str | None = None) -> dict:
        snapshot = self.get_project_snapshot(project_id, owner_user_id)
        return {
            "export_version": "1.0",
            "project_id": project_id,
            "snapshot": snapshot,
            "partner_review_notes": [
                "Sprint 1.0 includes provider-backed Ada Scout and Ada Empath paths.",
                "An in-process queue abstraction and structured event log are available for operational review.",
                "SQLite is used for durability in the packaged demo environment.",
            ],
        }

    def complete_first_seven_steps(self, project_id: str, owner_user_id: str | None = None, approval_feedback: str = "Proceed to IDEATE") -> dict:
        project = self._get_project_with_access(project_id, owner_user_id, require_write=True) if owner_user_id is not None else self.store.get_project(project_id)
        if project.current_phase != DFNPhase.EMPATHIZE or project.status != ProjectStatus.DRAFT:
            raise ValueError("Project must be at the start of EMPATHIZE to run steps 1-7.")

        self.start_current_phase(project_id, owner_user_id=owner_user_id)
        self.submit_decision(project_id, approved=True, feedback=approval_feedback, owner_user_id=owner_user_id)
        self.start_current_phase(project_id, owner_user_id=owner_user_id)

        snapshot = self.get_project_snapshot(project_id, owner_user_id)
        outputs = snapshot["outputs"]
        selected = [
            output
            for output in outputs
            if output["agent_id"] in {"agent-1", "agent-2", "agent-3", "agent-4", "agent-5"}
        ]
        return {
            "workflow": "first_seven_steps",
            "project_id": project_id,
            "status": snapshot["project"]["status"],
            "current_phase": snapshot["project"]["current_phase"],
            "included_steps": [
                "1-market-sizing",
                "2-competitive-landscape",
                "3-customer-persona",
                "4-industry-trends",
                "5-swot-and-porters",
                "6-pricing-and-opportunity-framing",
                "7-concept-generation",
            ],
            "outputs": selected,
            "recommended_endpoint_example": f"/projects/{project_id}/flows/first-seven-steps",
        }

    def complete_v1_workflow(self, project_id: str, owner_user_id: str | None = None, approval_feedback: str = "Proceed") -> dict:
        project = self._get_project_with_access(project_id, owner_user_id, require_write=True) if owner_user_id is not None else self.store.get_project(project_id)
        if project.current_phase != DFNPhase.EMPATHIZE or project.status != ProjectStatus.DRAFT:
            raise ValueError("Project must be at the start of EMPATHIZE to run the v1 workflow.")

        self.start_current_phase(project_id, owner_user_id=owner_user_id)
        self.submit_decision(project_id, approved=True, feedback=f"{approval_feedback} to IDEATE", owner_user_id=owner_user_id)
        self.start_current_phase(project_id, owner_user_id=owner_user_id)
        self.submit_decision(project_id, approved=True, feedback=f"{approval_feedback} to EVALUATE", owner_user_id=owner_user_id)
        self.start_current_phase(project_id, owner_user_id=owner_user_id)
        self.submit_decision(project_id, approved=True, feedback=f"{approval_feedback} to REALIZE", owner_user_id=owner_user_id)
        self.start_current_phase(project_id, owner_user_id=owner_user_id)

        snapshot = self.get_project_snapshot(project_id, owner_user_id)
        outputs = snapshot["outputs"]
        selected = [
            output
            for output in outputs
            if output["agent_id"] in {"agent-1", "agent-2", "agent-3", "agent-4", "agent-5", "agent-6", "agent-7", "agent-8", "agent-9"}
        ]
        return {
            "workflow": "v1_product_package",
            "project_id": project_id,
            "status": snapshot["project"]["status"],
            "current_phase": snapshot["project"]["current_phase"],
            "included_phases": ["EMPATHIZE", "IDEATE", "EVALUATE", "REALIZE"],
            "included_outputs": selected,
            "recommended_endpoint_example": f"/projects/{project_id}/flows/v1-package",
        }

    def complete_full_cycle(self, project_id: str, owner_user_id: str | None = None, approval_feedback: str = "Proceed") -> dict:
        project = self._get_project_with_access(project_id, owner_user_id, require_write=True) if owner_user_id is not None else self.store.get_project(project_id)
        if project.current_phase != DFNPhase.EMPATHIZE or project.status != ProjectStatus.DRAFT:
            raise ValueError("Project must be at the start of EMPATHIZE to run the full DFN cycle.")

        self.start_current_phase(project_id, owner_user_id=owner_user_id)
        self.submit_decision(project_id, approved=True, feedback=f"{approval_feedback} to IDEATE", owner_user_id=owner_user_id)
        self.start_current_phase(project_id, owner_user_id=owner_user_id)
        self.submit_decision(project_id, approved=True, feedback=f"{approval_feedback} to EVALUATE", owner_user_id=owner_user_id)
        self.start_current_phase(project_id, owner_user_id=owner_user_id)
        self.submit_decision(project_id, approved=True, feedback=f"{approval_feedback} to REALIZE", owner_user_id=owner_user_id)
        self.start_current_phase(project_id, owner_user_id=owner_user_id)
        self.submit_decision(project_id, approved=True, feedback=f"{approval_feedback} to MEASURE", owner_user_id=owner_user_id)
        self.start_current_phase(project_id, owner_user_id=owner_user_id)
        self.submit_decision(project_id, approved=True, feedback=f"{approval_feedback} to completion", owner_user_id=owner_user_id)

        snapshot = self.get_project_snapshot(project_id, owner_user_id)
        outputs = snapshot["outputs"]
        selected = [
            output
            for output in outputs
            if output["agent_id"] in {"agent-1", "agent-2", "agent-3", "agent-4", "agent-5", "agent-6", "agent-7", "agent-8", "agent-9", "agent-10", "agent-11", "agent-12"}
        ]
        return {
            "workflow": "full_dfn_cycle",
            "project_id": project_id,
            "status": snapshot["project"]["status"],
            "current_phase": snapshot["project"]["current_phase"],
            "included_phases": ["EMPATHIZE", "IDEATE", "EVALUATE", "REALIZE", "MEASURE"],
            "included_outputs": selected,
            "recommended_endpoint_example": f"/projects/{project_id}/flows/full-cycle",
        }

    def enqueue_current_phase(self, project_id: str, owner_user_id: str | None = None, requested_by: str = "human_user") -> dict:
        project = self._get_project_with_access(project_id, owner_user_id, require_write=True) if owner_user_id is not None else self.store.get_project(project_id)
        if project.status == ProjectStatus.COMPLETED:
            raise ValueError("Project is already completed.")
        if project.gate.status == GateStatus.PENDING:
            raise ValueError("Current phase is waiting for a human decision.")
        actor = self._actor_label(owner_user_id) if owner_user_id is not None else requested_by
        job = self.queue.enqueue_phase_execution(project.project_id, project.current_phase, requested_by=actor)
        return self.queue.snapshot(job.job_id)

    def process_job(self, job_id: str, owner_user_id: str | None = None) -> dict:
        if owner_user_id is not None:
            pending_job = self.store.get_job(job_id)
            self._get_project_with_access(pending_job.project_id, owner_user_id, require_write=True)
        job = self.queue.mark_running(job_id)
        try:
            self.start_current_phase(job.project_id, owner_user_id=owner_user_id, via_job_id=job.job_id, requested_by=job.requested_by)
            self.queue.mark_completed(job.job_id)
        except Exception as exc:
            self.queue.mark_failed(job.job_id, str(exc))
            raise
        return self.queue.snapshot(job.job_id)

    def start_current_phase(
        self,
        project_id: str,
        owner_user_id: str | None = None,
        via_job_id: str | None = None,
        requested_by: str | None = None,
    ) -> Project:
        project = self.store.get_project(project_id)
        if owner_user_id is not None:
            project = self._get_project_with_access(project_id, owner_user_id, require_write=True)
        actor = self._actor_label(owner_user_id) if owner_user_id is not None else (requested_by or "human_user")
        if project.status == ProjectStatus.COMPLETED:
            return project
        if project.gate.status == GateStatus.PENDING:
            raise ValueError("Current phase is waiting for a human decision.")

        project.status = ProjectStatus.IN_PROGRESS
        project.gate.phase = project.current_phase
        project.gate.status = GateStatus.NOT_OPEN
        self.store.save_project(project)
        run = self.store.add_run(
            ExecutionRun(
                project_id=project.project_id,
                phase=project.current_phase,
                status=RunStatus.STARTED,
                triggered_by=actor,
                summary=f"Started {project.current_phase.value} phase execution.",
            )
        )
        self.logger.log(
            project.project_id,
            event_type="phase_started",
            level="INFO",
            message=f"Started {project.current_phase.value} phase.",
            job_id=via_job_id,
            run_id=run.run_id,
            data={"phase": project.current_phase.value, "actor": actor},
        )

        for spec in PHASE_TO_AGENTS[project.current_phase]:
            self.store.add_message(
                Message(
                    sender="Ada Conductor",
                    receiver=spec.code_name,
                    message_type=MessageType.WORK_ORDER,
                    payload={"agent_id": spec.agent_id, "phase": project.current_phase.value},
                    project_id=project.project_id,
                    phase=project.current_phase,
                    step="dispatch_work_order",
                )
            )
            output = self.runner.run(project, spec)
            self.store.add_output(output)
            self.store.add_message(
                Message(
                    sender=spec.code_name,
                    receiver="Ada Conductor",
                    message_type=MessageType.RESULT,
                    payload={"output_id": output.output_id, "output_type": output.output_type},
                    project_id=project.project_id,
                    phase=project.current_phase,
                    step="return_result",
                )
            )

        project.status = ProjectStatus.WAITING_FOR_GATE
        project.gate.status = GateStatus.PENDING
        self.store.save_project(project)
        run.status = RunStatus.COMPLETED
        run.summary = f"Completed {project.current_phase.value} execution and opened a human gate."
        run.completed_at = project.updated_at
        self.store.save_run(run)
        self.logger.log(
            project.project_id,
            event_type="phase_completed",
            level="INFO",
            message=f"Completed {project.current_phase.value} phase and opened a gate.",
            job_id=via_job_id,
            run_id=run.run_id,
            data={"phase": project.current_phase.value, "actor": actor},
        )
        self.store.add_message(
            Message(
                sender="Ada Conductor",
                receiver="Human Review",
                message_type=MessageType.HUMAN_GATE_REQUEST,
                payload={"phase": project.current_phase.value},
                project_id=project.project_id,
                phase=project.current_phase,
                step="request_human_gate",
            )
        )
        return project

    def submit_decision(self, project_id: str, approved: bool, feedback: str | None = None, owner_user_id: str | None = None) -> Project:
        project = self.store.get_project(project_id)
        if owner_user_id is not None:
            project = self._get_project_with_access(project_id, owner_user_id, require_write=True)
        if project.gate.status != GateStatus.PENDING:
            raise ValueError("No pending gate for this project.")

        project.gate.status = GateStatus.APPROVED if approved else GateStatus.REJECTED
        project.gate.feedback = feedback
        project.gate.decided_at = None
        self.store.save_project(project)
        project.gate.decided_at = project.updated_at
        self.store.save_project(project)
        self.store.add_message(
            Message(
                sender="Human Review",
                receiver="Ada Conductor",
                message_type=MessageType.HUMAN_GATE_RESPONSE,
                payload={"approved": approved, "feedback": feedback},
                project_id=project.project_id,
                phase=project.current_phase,
                step="submit_human_gate",
            )
        )

        if not approved:
            project.status = ProjectStatus.FAILED
            self.store.save_project(project)
            runs = self.store.list_runs(project.project_id)
            if runs:
                runs[-1].status = RunStatus.REJECTED
                runs[-1].summary = f"{project.current_phase.value} gate rejected by human review."
                runs[-1].completed_at = project.updated_at
                self.store.save_run(runs[-1])
            self.logger.log(
                project.project_id,
                event_type="gate_rejected",
                level="WARN",
                message=f"Rejected gate for {project.current_phase.value}.",
                run_id=runs[-1].run_id if runs else None,
                data={"phase": project.current_phase.value, "feedback": feedback or "", "actor": self._actor_label(owner_user_id)},
            )
            return project

        phase_index = PHASE_ORDER.index(project.current_phase)
        if phase_index == len(PHASE_ORDER) - 1:
            project.status = ProjectStatus.COMPLETED
            self.store.save_project(project)
            self.logger.log(
                project.project_id,
                event_type="project_completed",
                level="INFO",
                message="Completed full DFN cycle.",
                data={"phase": project.current_phase.value, "actor": self._actor_label(owner_user_id)},
            )
            self.store.add_message(
                Message(
                    sender="Ada Conductor",
                    receiver="Ada Scout",
                    message_type=MessageType.FEEDBACK_LOOP,
                    payload={"next_cycle_context": "Project completed; route post-launch learning into EMPATHIZE."},
                    project_id=project.project_id,
                    phase=project.current_phase,
                    step="close_feedback_loop",
                )
            )
            return project

        project.current_phase = PHASE_ORDER[phase_index + 1]
        project.gate.phase = project.current_phase
        project.gate.status = GateStatus.NOT_OPEN
        project.gate.feedback = None
        project.gate.decided_at = None
        project.status = ProjectStatus.DRAFT
        self.store.save_project(project)
        self.logger.log(
            project.project_id,
            event_type="gate_approved",
            level="INFO",
            message=f"Approved gate and advanced to {project.current_phase.value}.",
            data={"next_phase": project.current_phase.value, "feedback": feedback or "", "actor": self._actor_label(owner_user_id)},
        )
        return project
