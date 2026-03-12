from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ada_iq.models import UserRole
from ada_iq.orchestrator import Orchestrator


def _load_seed_records(seed_path: Path) -> list[dict[str, Any]]:
    return json.loads(seed_path.read_text(encoding="utf-8"))


def ensure_admin_user(orchestrator: Orchestrator, email: str, password: str) -> dict:
    try:
        user = orchestrator.store.get_user_by_email(email)
        if user.role != UserRole.ADMIN:
            raise ValueError(f"Bootstrap admin email {email} already exists as a non-admin user.")
        return {"user": {"user_id": user.user_id, "email": user.email, "role": user.role.value}}
    except KeyError:
        return orchestrator.register_user(email, password, role=UserRole.ADMIN)


def seed_demo_projects(
    orchestrator: Orchestrator,
    seed_path: str | Path,
    owner_email: str = "demo@adaiq.local",
    owner_password: str = "demo12345",
) -> int:
    path = Path(seed_path)
    if not path.exists():
        return 0
    user_record = ensure_admin_user(orchestrator, owner_email, owner_password)["user"]
    user = orchestrator.store.get_user(user_record["user_id"])
    if orchestrator.list_projects_snapshot(user.user_id):
        return 0

    created = 0
    for record in _load_seed_records(path):
        project = orchestrator.create_project(owner_user_id=user.user_id, name=record["name"], brief=record["brief"])
        actions = record.get("actions", [])
        for action in actions:
            if action["type"] == "start_phase":
                orchestrator.start_current_phase(project.project_id)
            elif action["type"] == "submit_decision":
                orchestrator.submit_decision(
                    project.project_id,
                    approved=action["approved"],
                    feedback=action.get("feedback"),
                )
        created += 1
    return created
