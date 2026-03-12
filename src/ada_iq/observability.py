from __future__ import annotations

from ada_iq.models import EventLog
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
        event = EventLog(
            project_id=project_id,
            event_type=event_type,
            level=level,
            message=message,
            job_id=job_id,
            run_id=run_id,
            data=data or {},
        )
        return self.store.add_event(event)
