# HR Assist - Demo (with funnel, dashboard, uploads, Unity Catalog Volume storage)

## Features
- **Job Descriptions**: paste JD text or upload a PDF/DOCX/TXT file
- **Candidates**: paste resume text or upload a PDF/DOCX/TXT file
- **Matching & Screening**: run a keyword-overlap match score, then move
  each match through funnel stages (applied → screened → shortlisted →
  interview → offer → hired, or rejected) via a dropdown
- **Hiring Funnel**: a funnel chart of counts at each stage, filterable
  by job
- **Dashboard**: totals, average match score, candidates per job, and
  candidates by stage

Matching is intentionally simple (keyword overlap in `matching.py`) so
the demo works with zero extra API keys. Swap `score_match()` for an
LLM call once you're ready to wire in your real matcher.

## Deploy to Databricks Apps

1. Push these 7 files to a GitHub repo, at the repo root:
   app.py, db.py, matching.py, file_parsing.py, storage.py, app.yaml, requirements.txt
2. In Databricks: + New > App, connect it to this repo.
3. In the app's Settings > Resources, click **Add resource > Database**,
   pick your Lakebase project, branch "production", database
   "databricks_postgres", permission "Can connect and create", and set
   the **Resource key to `postgres`**.
4. In Catalog Explorer, create catalog `hr_assist` > schema `demo` >
   volume `files` (if you haven't already).
5. Back in the app's Settings > Resources, click **Add resource > Volume**,
   select hr_assist.demo.files, permission "Can read and write", and set
   the **Resource key to `files_volume`**.
6. Edit `app.yaml` and set `LAKEBASE_INSTANCE_NAME` to your actual
   Lakebase project name. Commit the change.
7. Click Deploy. Tables are created automatically on first run.
8. Open the app URL, upload a resume or JD, then check Catalog Explorer
   under Volumes > hr_assist > demo > files — the actual file should be
   sitting there, governed by Unity Catalog.

## Note on the schema change
If you already deployed the earlier (simpler) version of this demo, the
`matches` table there didn't have a `stage` column, and there was a
separate `screenings` table. This version merges screening status into
`matches.stage` directly. If you're upgrading from the old version, drop
the old tables first via the Lakebase SQL editor:
```sql
DROP TABLE IF EXISTS screenings;
DROP TABLE IF EXISTS matches;
```
Then redeploy — they'll be recreated with the new schema. (Fine to do
for a demo; don't do this if you have real data you care about.)

## Local dev
```
pip install -r requirements.txt
export PGHOST=... PGUSER=... PGDATABASE=... PGPORT=5432 PGSSLMODE=require
export LAKEBASE_INSTANCE_NAME=your-project-name
streamlit run app.py
```
