from app.pipeline.progress import complete_job, get_job, init_job, update_job


def test_pipeline_progress_lifecycle():
    init_job("job-1")
    update_job("job-1", step="knowledge", percent=40, message="Retrieving evidence")
    complete_job("job-1")

    job = get_job("job-1")
    assert job["status"] == "completed"
    assert job["percent"] == 100
    assert job["step"] == "complete"
