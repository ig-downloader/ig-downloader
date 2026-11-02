import logging
from concurrent.futures import ThreadPoolExecutor

from . import store
from .config import settings
from .schemas import JobStatus, JobType
from .scraper import ScrapeError, download_post, download_profile

log = logging.getLogger(__name__)
pool = ThreadPoolExecutor(max_workers=settings.max_workers)


def _run(job_id: str):
    job = store.get(job_id)
    store.update(job_id, status=JobStatus.running)
    try:
        if job.type == JobType.post:
            files = download_post(job_id, job.target)
        else:
            files = download_profile(job_id, job.target, job.limit)
        store.update(job_id, status=JobStatus.done, files=files)
        log.info("job %s done (%d files)", job_id, len(files))
    except ScrapeError as e:
        store.update(job_id, status=JobStatus.failed, error=f"{e.code}: {e}")
    except Exception as e:  # never let a worker die silently
        log.exception("job %s crashed", job_id)
        store.update(job_id, status=JobStatus.failed, error=f"500: {e}")


def submit(job_id: str):
    pool.submit(_run, job_id)
