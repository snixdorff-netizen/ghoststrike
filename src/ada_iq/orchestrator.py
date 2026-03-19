from __future__ import annotations

from collections.abc import Sequence
from ada_iq.models import utcnow

from ada_iq.auth import hash_password, new_session_token, verify_password
from ada_iq.agents import PHASE_TO_AGENTS, StubAgentRunner
from ada_iq.models import (
    ComplianceProfile,
    ComplianceStatus,
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
    SmartBriefModule,
    SmartBriefRevision,
    SmartProductBrief,
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

    def create_session_for_email(self, email: str) -> dict:
        try:
            user = self.store.get_user_by_email(email)
        except KeyError as exc:
            raise ValueError("Demo user is not configured.") from exc
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

    def get_admin_dashboard(self, requester_user_id: str) -> dict:
        requester = self.store.get_user(requester_user_id)
        if requester.role != UserRole.ADMIN:
            raise PermissionError("Admin access required.")

        users = self.store.list_users()
        projects = self.store.list_projects()
        feedback_events = []
        event_feed = []
        queued_jobs = 0
        completed_jobs = 0
        active_gates = 0
        completed_projects = 0

        for project in projects:
            if project.gate.status == GateStatus.PENDING:
                active_gates += 1
            if project.status == ProjectStatus.COMPLETED:
                completed_projects += 1

            project_events = self.store.list_events(project.project_id)
            event_feed.extend(project_events)
            feedback_events.extend([event for event in project_events if event.event_type == "alpha_feedback"])

            for job in self.store.list_jobs(project.project_id):
                if job.status.value == "QUEUED":
                    queued_jobs += 1
                if job.status.value == "COMPLETED":
                    completed_jobs += 1

        feedback_by_category: dict[str, int] = {}
        for event in feedback_events:
            category = str(event.data.get("category", "GENERAL"))
            feedback_by_category[category] = feedback_by_category.get(category, 0) + 1

        latest_activity = [
            {
                "project_id": event.project_id,
                "event_type": event.event_type,
                "message": event.message,
                "timestamp": dataclass_to_api_dict(event.timestamp),
                "actor": event.data.get("actor", "system"),
            }
            for event in sorted(event_feed, key=lambda item: item.timestamp, reverse=True)[:8]
        ]

        return {
            "build_label": None,
            "user_count": len(users),
            "project_count": len(projects),
            "active_gates": active_gates,
            "completed_projects": completed_projects,
            "queued_jobs": queued_jobs,
            "completed_jobs": completed_jobs,
            "feedback_count": len(feedback_events),
            "feedback_by_category": feedback_by_category,
            "latest_activity": latest_activity,
        }

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

    def _coerce_list(self, value: Sequence[str] | str | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(item).strip() for item in value if str(item).strip()]

    def _build_smart_brief_summary(self, name: str, brief: SmartProductBrief) -> str:
        competitor_text = ", ".join(brief.competitive_set) if brief.competitive_set else "the incumbent competitive set"
        constraints_text = brief.constraints or "normal launch, technical, and brand constraints"
        return (
            f"Build a smart product brief for {name} in the {brief.category} category at {brief.price_point}. "
            f"Target {brief.consumer_profile} in {brief.geo_market} against {competitor_text}. "
            f"Respect these brand guardrails: {brief.brand_guardrails or 'maintain premium category fit'}. "
            f"Account for these constraints: {constraints_text}. "
            f"Launch timing centers on {brief.launch_season or 'the next planning cycle'}. "
            f"Additional context: {brief.open_context or 'No extra context provided.'}"
        )

    def _build_smart_brief_modules(self, brief: SmartProductBrief) -> list[SmartBriefModule]:
        competitors = ", ".join(brief.competitive_set) or "the incumbent competitive set"
        constraints = brief.constraints or "No explicit constraints captured yet."
        guardrails = brief.brand_guardrails or "Maintain premium category fit and clear brand coherence."
        return [
            SmartBriefModule(
                "executive_summary",
                "Executive Summary",
                brief.generated_summary,
                ["human_project_brief"],
            ),
            SmartBriefModule(
                "consumer_insight",
                "Consumer Insight",
                f"The initial wedge centers on {brief.consumer_profile}. The working assumption is that this buyer will respond when the product clearly resolves a repeat use-case friction and signals premium confidence at {brief.price_point}.",
                ["human_project_brief"],
            ),
            SmartBriefModule(
                "market_context",
                "Market Context",
                f"The first market focus is {brief.geo_market}. Ada IQ should treat this as the launch wedge and evaluate whether the category dynamics support premium positioning, specialized channel adoption, and a fast proof-of-demand cycle.",
                ["human_project_brief"],
            ),
            SmartBriefModule(
                "competitive_intelligence",
                "Competitive Intelligence",
                f"The current comparison set is {competitors}. The brief should frame differentiation around where incumbents leave a clear experiential, brand, or use-case gap rather than competing on generic parity.",
                ["human_project_brief"],
            ),
            SmartBriefModule(
                "trend_signal",
                "Trend Signal",
                f"Launch timing is anchored to {brief.launch_season or 'the next planning cycle'}. The trend lens should examine whether consumer behavior, category premiumization, and channel timing create urgency for this concept now rather than later.",
                ["human_project_brief"],
            ),
            SmartBriefModule(
                "strategic_directions",
                "Strategic Directions",
                f"Strategically, Ada IQ should protect these brand guardrails: {guardrails} The resulting concept directions should feel commercially specific, not generically innovative.",
                ["human_project_brief"],
            ),
            SmartBriefModule(
                "design_requirements",
                "Design Requirements",
                f"Design should prioritize a product that feels credible to {brief.consumer_profile}, earns its {brief.price_point} positioning, and creates visible differentiation without violating the stated brand rules.",
                ["human_project_brief"],
            ),
            SmartBriefModule(
                "technical_constraints",
                "Technical Constraints",
                f"Key constraints captured in the brief: {constraints} These constraints should shape feasibility scoring, concept narrowing, and launch sequencing from the outset.",
                ["human_project_brief"],
            ),
            SmartBriefModule(
                "success_metrics",
                "Success Metrics",
                "The first success bar is simple: prove that the brief creates sharper market framing, more credible consumer insight, and a clearer decision path than a traditional product intake. Secondary metrics should track concept confidence, stakeholder clarity, and readiness to advance.",
                ["ada_iq_system"],
            ),
        ]

    def _build_smart_brief(self, payload: dict | None, name: str, brief: str) -> SmartProductBrief | None:
        if payload is None:
            return None
        smart_brief = SmartProductBrief(
            category=payload.get("category", "").strip(),
            price_point=payload.get("price_point", "").strip(),
            consumer_profile=payload.get("consumer_profile", "").strip(),
            geo_market=payload.get("geo_market", "").strip(),
            competitive_set=self._coerce_list(payload.get("competitive_set")),
            brand_guardrails=payload.get("brand_guardrails", "").strip(),
            constraints=payload.get("constraints", "").strip(),
            launch_season=payload.get("launch_season", "").strip(),
            uploaded_docs=self._coerce_list(payload.get("uploaded_docs")),
            open_context=payload.get("open_context", "").strip(),
        )
        smart_brief.generated_summary = brief or self._build_smart_brief_summary(name, smart_brief)
        smart_brief.modules = self._build_smart_brief_modules(smart_brief)
        return smart_brief

    def _record_module_revision(self, module: SmartBriefModule, updated_by: str) -> None:
        module.revisions.append(
            SmartBriefRevision(
                version=module.version,
                content=module.content,
                updated_at=module.updated_at,
                updated_by=updated_by,
                citations=list(module.citations),
            )
        )

    def _refresh_smart_brief_from_outputs(self, project: Project) -> None:
        if not project.smart_brief:
            return
        outputs = {
            output.agent_id: output
            for output in self.store.list_outputs(project.project_id)
            if output.agent_id in {"agent-1", "agent-2"}
        }
        modules_by_key = {module.key: module for module in project.smart_brief.modules}

        scout = outputs.get("agent-1")
        if scout:
            market_context = modules_by_key.get("market_context")
            if market_context:
                self._record_module_revision(market_context, market_context.updated_by)
                market_context.content = (
                    f"{scout.data.get('summary', market_context.content)} Geography focus: {scout.data.get('geography_focus', project.smart_brief.geo_market)}."
                )
                market_context.citations = [
                    citation.get("title", "Source")
                    for citation in scout.data.get("citations", [])
                ]
                market_context.version += 1
                market_context.updated_at = utcnow()
                market_context.updated_by = "Ada Scout"
            competitive = modules_by_key.get("competitive_intelligence")
            if competitive:
                self._record_module_revision(competitive, competitive.updated_by)
                competitive.content = (
                    f"Primary comparison set: {', '.join(scout.data.get('top_competitors', project.smart_brief.competitive_set))}. "
                    f"Whitespace: {scout.data.get('whitespace_opportunity', competitive.content)}"
                )
                competitive.citations = [
                    citation.get("title", "Source")
                    for citation in scout.data.get("citations", [])
                ]
                competitive.version += 1
                competitive.updated_at = utcnow()
                competitive.updated_by = "Ada Scout"
            trend = modules_by_key.get("trend_signal")
            if trend:
                self._record_module_revision(trend, trend.updated_by)
                trend.content = (
                    f"Trend signals: {', '.join(scout.data.get('trend_signals', [])) or trend.content}"
                )
                trend.citations = [citation.get("title", "Source") for citation in scout.data.get("citations", [])]
                trend.version += 1
                trend.updated_at = utcnow()
                trend.updated_by = "Ada Scout"

        empath = outputs.get("agent-2")
        if empath:
            consumer = modules_by_key.get("consumer_insight")
            if consumer:
                self._record_module_revision(consumer, consumer.updated_by)
                persona = empath.data.get("primary_persona", {})
                consumer.content = (
                    f"{empath.data.get('summary', consumer.content)} Primary persona: {persona.get('name', 'Unknown')} with job-to-be-done '{persona.get('job_to_be_done', '')}'."
                )
                consumer.citations = [
                    citation.get("title", "Source")
                    for citation in empath.data.get("citations", [])
                ]
                consumer.version += 1
                consumer.updated_at = utcnow()
                consumer.updated_by = "Ada Empath"
            design = modules_by_key.get("design_requirements")
            if design:
                self._record_module_revision(design, design.updated_by)
                needs = empath.data.get("need_hierarchy", [])
                primary_need = needs[0]["need"] if needs else "clear functional improvement"
                design.content = (
                    f"Design should prioritize {primary_need} for {project.smart_brief.consumer_profile}, while preserving {project.smart_brief.brand_guardrails or 'premium category fit'}."
                )
                design.citations = [citation.get("title", "Source") for citation in empath.data.get("citations", [])]
                design.version += 1
                design.updated_at = utcnow()
                design.updated_by = "Ada Empath"
        project.smart_brief.version += 1
        project.smart_brief.updated_at = utcnow()

    def update_smart_brief_module(
        self,
        project_id: str,
        module_key: str,
        content: str,
        owner_user_id: str,
    ) -> dict:
        project = self._get_project_with_access(project_id, owner_user_id, require_write=True)
        if not project.smart_brief:
            raise ValueError("This project does not have a Smart Product Brief.")
        module = next((item for item in project.smart_brief.modules if item.key == module_key), None)
        if module is None:
            raise KeyError(module_key)
        self._record_module_revision(module, module.updated_by)
        module.content = content.strip()
        module.version += 1
        module.updated_at = utcnow()
        module.updated_by = self._actor_label(owner_user_id)
        project.smart_brief.version += 1
        project.smart_brief.updated_at = utcnow()
        self.store.save_project(project)
        self.logger.log(
            project.project_id,
            event_type="smart_brief_module_updated",
            level="INFO",
            message=f"Updated Smart Product Brief module {module.title}.",
            data={"actor": self._actor_label(owner_user_id), "module_key": module.key, "module_version": module.version},
        )
        return self.get_smart_brief_package(project_id, owner_user_id)

    def create_project(
        self,
        name: str,
        brief: str,
        owner_user_id: str = "system",
        smart_brief: dict | None = None,
        tenant_id: str = "preview",
    ) -> Project:
        structured_brief = self._build_smart_brief(smart_brief, name, brief)
        brief_text = structured_brief.generated_summary if structured_brief else brief
        project = Project(
            name=name,
            brief=brief_text,
            owner_user_id=owner_user_id,
            tenant_id=tenant_id or "preview",
            smart_brief=structured_brief,
            compliance=ComplianceProfile(status=ComplianceStatus.TRACKED),
        )
        return self.store.create_project(project)

    def _actor_label(self, user_id: str | None) -> str:
        if user_id is None:
            return "human_user"
        try:
            return self.store.get_user(user_id).email
        except KeyError:
            return user_id

    def _project_api_dict(self, project: Project) -> dict:
        payload = dataclass_to_api_dict(project)
        payload["owner_email"] = self._actor_label(project.owner_user_id)
        return payload

    def _collaborator_api_dict(self, collaborator: ProjectCollaborator) -> dict:
        payload = dataclass_to_api_dict(collaborator)
        payload["email"] = self._actor_label(collaborator.user_id)
        return payload

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
            "project": self._project_api_dict(project),
            "messages": dataclass_to_api_dict(self.store.list_messages(project_id)),
            "outputs": dataclass_to_api_dict(self.store.list_outputs(project_id)),
            "runs": dataclass_to_api_dict(self.store.list_runs(project_id)),
            "jobs": dataclass_to_api_dict(self.store.list_jobs(project_id)),
            "events": dataclass_to_api_dict(self.store.list_events(project_id)),
            "feedback": self.list_project_feedback(project_id, owner_user_id) if owner_user_id is not None else [
                dataclass_to_api_dict(event) for event in self.store.list_events(project_id) if event.event_type == "alpha_feedback"
            ],
            "collaborators": [self._collaborator_api_dict(collaborator) for collaborator in self.store.list_collaborators(project_id)],
        }

    def list_projects_snapshot(self, owner_user_id: str | None = None) -> list[dict]:
        return [self._project_api_dict(project) for project in self.store.list_projects(owner_user_id)]

    def export_project_snapshot(self, project_id: str, owner_user_id: str | None = None) -> dict:
        snapshot = self.get_project_snapshot(project_id, owner_user_id)
        smart_brief = snapshot["project"].get("smart_brief")
        return {
            "export_version": "1.0",
            "project_id": project_id,
            "snapshot": snapshot,
            "smart_brief_export": {
                "project_name": snapshot["project"]["name"],
                "tenant_id": snapshot["project"].get("tenant_id"),
                "compliance": snapshot["project"].get("compliance"),
                "summary": smart_brief.get("generated_summary") if smart_brief else snapshot["project"]["brief"],
                "modules": smart_brief.get("modules", []) if smart_brief else [],
            },
            "partner_review_notes": [
                "Sprint 1.0 includes provider-backed Ada Scout and Ada Empath paths.",
                "An in-process queue abstraction and structured event log are available for operational review.",
                "SQLite is used for durability in the packaged demo environment.",
            ],
        }

    def get_smart_brief_package(self, project_id: str, owner_user_id: str | None = None) -> dict:
        snapshot = self.get_project_snapshot(project_id, owner_user_id)
        project = snapshot["project"]
        smart_brief = project.get("smart_brief")
        if not smart_brief:
            raise ValueError("This project does not have a Smart Product Brief package.")

        related_outputs = [
            output
            for output in snapshot["outputs"]
            if output["agent_id"] in {"agent-1", "agent-2"}
        ]
        return {
            "package_version": "1.0",
            "package_type": "smart_product_brief",
            "project_id": project_id,
            "project_name": project["name"],
            "tenant_id": project.get("tenant_id"),
            "compliance": project.get("compliance"),
            "summary": smart_brief.get("generated_summary"),
            "input": {
                "category": smart_brief.get("category"),
                "price_point": smart_brief.get("price_point"),
                "consumer_profile": smart_brief.get("consumer_profile"),
                "geo_market": smart_brief.get("geo_market"),
                "competitive_set": smart_brief.get("competitive_set", []),
                "brand_guardrails": smart_brief.get("brand_guardrails"),
                "constraints": smart_brief.get("constraints"),
                "launch_season": smart_brief.get("launch_season"),
                "uploaded_docs": smart_brief.get("uploaded_docs", []),
                "open_context": smart_brief.get("open_context"),
            },
            "modules": smart_brief.get("modules", []),
            "supporting_outputs": related_outputs,
            "recommended_next_step": (
                "Review the Smart Product Brief modules, then approve the EMPATHIZE gate or continue into the V1 package."
            ),
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
            output.tenant_id = project.tenant_id
            output.compliance_status = project.compliance.status
            output.data_classification = project.compliance.data_classification
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

        self._refresh_smart_brief_from_outputs(project)
        self.store.save_project(project)

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
