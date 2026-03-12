from __future__ import annotations

import time

from ada_iq.config import load_settings
from ada_iq.models import JobStatus
from ada_iq.orchestrator import Orchestrator
from ada_iq.store import SQLiteContextStore


def run_worker(poll_interval_seconds: float = 2.0) -> None:
    settings = load_settings()
    orchestrator = Orchestrator(SQLiteContextStore(settings.database_path))

    while True:
        jobs = orchestrator.store.list_jobs()
        queued_jobs = [job for job in jobs if job.status == JobStatus.QUEUED]
        for job in queued_jobs:
            try:
                orchestrator.process_job(job.job_id)
            except Exception:
                # The orchestrator already persists failure state for the job.
                pass
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    run_worker()
