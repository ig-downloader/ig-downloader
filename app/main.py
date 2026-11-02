import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import store, worker
from .config import settings
from .schemas import CreateJob, Job

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

limiter = Limiter(key_func=get_remote_address)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_key(key: str = Security(api_key_header)):
    if key != settings.api_key:
        raise HTTPException(401, "invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    yield
    worker.pool.shutdown(wait=False)


app = FastAPI(title="Instagram Public Media Downloader", version="1.0.0",
              lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/jobs", response_model=Job, status_code=202,
          dependencies=[Depends(require_key)])
@limiter.limit(settings.rate_limit)
def create_job(request: Request, body: CreateJob):
    try:
        type_, target = body.resolve()
    except ValueError as e:
        raise HTTPException(422, str(e))
    job = store.create(type_, target, body.limit)
    worker.submit(job.id)
    return job


@app.get("/api/v1/jobs/{job_id}", response_model=Job,
         dependencies=[Depends(require_key)])
def get_job(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@app.get("/api/v1/files/{path:path}", dependencies=[Depends(require_key)])
def get_file(path: str):
    base = settings.download_dir.resolve()
    full = (base / path).resolve()
    if base not in full.parents or not full.is_file():   # blocks path traversal
        raise HTTPException(404, "file not found")
    return FileResponse(full)
