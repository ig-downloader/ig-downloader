import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from .config import settings
from .schemas import Job, JobStatus, JobType

_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(settings.db_path, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS jobs(
            id TEXT PRIMARY KEY, type TEXT, target TEXT, lim INTEGER,
            status TEXT, error TEXT, files TEXT,
            created_at TEXT, updated_at TEXT)""")


def _now():
    return datetime.now(timezone.utc).isoformat()


def create(type_: JobType, target: str, limit: int) -> Job:
    jid, now = uuid.uuid4().hex, _now()
    with _lock, _conn() as c:
        c.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)",
                  (jid, type_.value, target, limit, JobStatus.queued.value,
                   None, "[]", now, now))
    return get(jid)


def update(jid: str, **fields):
    if "files" in fields:
        fields["files"] = json.dumps(fields["files"])
    if "status" in fields:
        fields["status"] = fields["status"].value
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k}=?" for k in fields)
    with _lock, _conn() as c:
        c.execute(f"UPDATE jobs SET {cols} WHERE id=?", (*fields.values(), jid))


def get(jid: str) -> Job | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    if not r:
        return None
    return Job(id=r["id"], type=r["type"], target=r["target"], limit=r["lim"],
               status=r["status"], error=r["error"], files=json.loads(r["files"]),
               created_at=r["created_at"], updated_at=r["updated_at"])
