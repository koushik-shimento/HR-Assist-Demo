import os
import uuid
import psycopg
from psycopg_pool import ConnectionPool
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

FUNNEL_STAGES = ["applied", "screened", "shortlisted", "interview", "offer", "hired", "rejected"]


class OAuthConnection(psycopg.Connection):
    """Postgres connection that fetches a fresh Lakebase OAuth token each time."""

    @classmethod
    def connect(cls, conninfo="", **kwargs):
        cred = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[os.environ["LAKEBASE_INSTANCE_NAME"]],
        )
        kwargs["password"] = cred.token
        return super().connect(conninfo, **kwargs)


pool = ConnectionPool(
    conninfo=(
        f"dbname={os.environ.get('PGDATABASE', '')} "
        f"user={os.environ.get('PGUSER', '')} "
        f"host={os.environ.get('PGHOST', '')} "
        f"port={os.environ.get('PGPORT', '5432')} "
        f"sslmode={os.environ.get('PGSSLMODE', 'require')}"
    ),
    connection_class=OAuthConnection,
    min_size=1,
    max_size=5,
    open=True,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    requirements_text TEXT NOT NULL,
    jd_filename TEXT,
    jd_volume_path TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    resume_text TEXT NOT NULL,
    resume_filename TEXT,
    resume_volume_path TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    candidate_id INTEGER REFERENCES candidates(id),
    job_id INTEGER REFERENCES jobs(id),
    score NUMERIC NOT NULL,
    matched_keywords TEXT,
    stage TEXT NOT NULL DEFAULT 'applied',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(candidate_id, job_id)
);
"""


def init_schema():
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()


def run(sql, params=(), fetch=False, fetchone=False):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetchone:
                cols = [d.name for d in cur.description]
                row = cur.fetchone()
                return dict(zip(cols, row)) if row else None
            if fetch:
                cols = [d.name for d in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.commit()
