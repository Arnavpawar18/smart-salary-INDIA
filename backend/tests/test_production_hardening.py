from fastapi.testclient import TestClient

from app.core.job_queue import JobQueueService, JobStatus, JobType
from app.main import app

client = TestClient(app)


def test_owasp_security_headers_present():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Strict-Transport-Security" in response.headers


def test_async_job_queue_lifecycle():
    # 1. Create Job
    job = JobQueueService.create_job(
        job_type=JobType.RECONCILE_PAYSLIP,
        payload={"document_id": 42, "employee_id": 101},
    )
    assert job.status == JobStatus.QUEUED
    assert job.job_id.startswith("job_")

    # 2. Get Job
    retrieved = JobQueueService.get_job(job.job_id)
    assert retrieved is not None
    assert retrieved.job_type == JobType.RECONCILE_PAYSLIP

    # 3. Complete Job
    completed = JobQueueService.complete_job(job.job_id, {"reconciliation_status": "MATCHED"})
    assert completed.status == JobStatus.COMPLETED
    assert completed.result == {"reconciliation_status": "MATCHED"}
