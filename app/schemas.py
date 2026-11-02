import re
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator

POST_RE = re.compile(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]{5,})")
USER_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")


class JobType(str, Enum):
    post = "post"
    profile = "profile"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class CreateJob(BaseModel):
    url: str | None = Field(None, description="Post/reel URL")
    username: str | None = Field(None, description="Public profile username")
    limit: int = Field(6, ge=1, le=50)

    @field_validator("username")
    @classmethod
    def check_username(cls, v):
        if v is not None and not USER_RE.match(v):
            raise ValueError("invalid Instagram username")
        return v

    def resolve(self) -> tuple[JobType, str]:
        if self.url:
            m = POST_RE.search(self.url)
            if not m:
                raise ValueError("URL must be an Instagram post/reel link")
            return JobType.post, m.group(1)
        if self.username:
            return JobType.profile, self.username
        raise ValueError("provide either 'url' or 'username'")


class Job(BaseModel):
    id: str
    type: JobType
    target: str
    limit: int
    status: JobStatus
    error: str | None = None
    files: list[str] = []
    created_at: datetime
    updated_at: datetime
