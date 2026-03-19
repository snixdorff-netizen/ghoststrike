from __future__ import annotations

from ada_iq.models import Job, JobStatus
from ada_iq.observability import EventLogger
from ada_iq.store import ContextStore, dataclass_to_api_dict


class InProcessJobQueue:
    def __init__(self, store: ContextStore, logger: EventLogger) -> None:
        self.store = store
        self.logger = logger

    def enqueue_phase_execution(self, project_id: str, phase, requested_by: str = "human_user") -> Job:
        project = self.store.get_project(project_id)
        job = Job(
            project_id=project_id,
            phase=phase,
            status=JobStatus.QUEUED,
            requested_by=requested_by,
            tenant_id=project.tenant_id,
            compliance_status=project.compliance.status,
            data_classification=project.compliance.data_classification,
        )
        self.store.add_job(job)
        self.logger.log(
            project_id,
            event_type="job_enqueued",
            level="INFO",
            message=f"Queued {phase.value} phase execution.",
            job_id=job.job_id,
            data={"phase": phase.value, "job_type": job.job_type, "actor": requested_by},
        )
        return job

    def mark_running(self, job_id: str) -> Job:
        job = self.store.get_job(job_id)
        job.status = JobStatus.RUNNING
        self.store.save_job(job)
        self.logger.log(
            job.project_id,
            event_type="job_started",
            level="INFO",
            message=f"Started queued job for {job.phase.value}.",
            job_id=job.job_id,
            data={"phase": job.phase.value, "actor": job.requested_by},
        )
        return job

    def mark_completed(self, job_id: str) -> Job:
        job = self.store.get_job(job_id)
        job.status = JobStatus.COMPLETED
        self.store.save_job(job)
        self.logger.log(
            job.project_id,
            event_type="job_completed",
            level="INFO",
            message=f"Completed queued job for {job.phase.value}.",
            job_id=job.job_id,
            data={"phase": job.phase.value, "actor": job.requested_by},
        )
        return job

    def mark_failed(self, job_id: str, error: str) -> Job:
        job = self.store.get_job(job_id)
        job.status = JobStatus.FAILED
        job.error = error
        self.store.save_job(job)
        self.logger.log(
            job.project_id,
            event_type="job_failed",
            level="ERROR",
            message=error,
            job_id=job.job_id,
            data={"phase": job.phase.value, "actor": job.requested_by},
        )
        return job

    def snapshot(self, job_id: str) -> dict:
        return dataclass_to_api_dict(self.store.get_job(job_id))
