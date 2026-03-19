from __future__ import annotations

from ada_iq.models import ComplianceStatus, EventLog
from ada_iq.store import ContextStore


class EventLogger:
    def __init__(self, store: ContextStore) -> None:
        self.store = store

    def log(
        self,
        project_id: str,
        event_type: str,
        level: str,
        message: str,
        *,
        job_id: str | None = None,
        run_id: str | None = None,
        data: dict | None = None,
    ) -> EventLog:
        tenant_id = "preview"
        compliance_status = ComplianceStatus.TRACKED
        data_classification = "CONFIDENTIAL"
        try:
            project = self.store.get_project(project_id)
            tenant_id = project.tenant_id
            compliance_status = project.compliance.status
            data_classification = project.compliance.data_classification
        except Exception:
            pass
        event = EventLog(
            project_id=project_id,
            event_type=event_type,
            level=level,
            message=message,
            tenant_id=tenant_id,
            compliance_status=compliance_status,
            data_classification=data_classification,
            job_id=job_id,
            run_id=run_id,
            data=data or {},
        )
        return self.store.add_event(event)
