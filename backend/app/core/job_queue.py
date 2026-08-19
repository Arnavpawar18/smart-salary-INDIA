import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class JobType(StrEnum):
    UPLOAD_PAYSLIP = "UPLOAD_PAYSLIP"
    EXTRACT_PDF = "EXTRACT_PDF"
    RUN_OCR = "RUN_OCR"
    RECONCILE_PAYSLIP = "RECONCILE_PAYSLIP"
    INGEST_KNOWLEDGE = "INGEST_KNOWLEDGE"
    GENERATE_EMBEDDINGS = "GENERATE_EMBEDDINGS"
    GENERATE_REPORT = "GENERATE_REPORT"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class JobResultDTO:
    job_id: str
    job_type: JobType
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error_message: str | None = None


class JobQueueService:
    """
    Asynchronous background job manager for heavy tasks (OCR, bulk payslip ingestion, report generation).
    Decouples long-running computation from synchronous Vercel HTTP serverless request lifecycles.
    """

    _jobs: dict[str, JobResultDTO] = {}

    @classmethod
    def create_job(cls, job_type: JobType, payload: dict[str, Any]) -> JobResultDTO:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        job = JobResultDTO(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
            payload=payload,
        )
        cls._jobs[job_id] = job
        return job

    @classmethod
    def get_job(cls, job_id: str) -> JobResultDTO | None:
        return cls._jobs.get(job_id)

    @classmethod
    def complete_job(cls, job_id: str, result: dict[str, Any]) -> JobResultDTO:
        job = cls._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")
        job.status = JobStatus.COMPLETED
        job.result = result
        job.updated_at = datetime.now(UTC)
        return job

    @classmethod
    def fail_job(cls, job_id: str, error_message: str) -> JobResultDTO:
        job = cls._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")
        job.status = JobStatus.FAILED
        job.error_message = error_message
        job.updated_at = datetime.now(UTC)
        return job
