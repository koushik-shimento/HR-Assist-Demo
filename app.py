import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import pool, init_schema, run, FUNNEL_STAGES
from matching import score_match
from file_parsing import extract_text
from storage import save_upload

st.set_page_config(page_title="HR Assist - Demo", layout="wide")

try:
    init_schema()
except Exception as e:
    st.warning(f"Schema init: {e}")


st.title("HR Assist — Demo")

tab_jobs, tab_candidates, tab_matching, tab_funnel, tab_dashboard = st.tabs(
    ["Job Descriptions", "Candidates", "Matching & Screening", "Hiring Funnel", "Dashboard"]
)

# ---------- Job Descriptions ----------
with tab_jobs:
    st.subheader("Add a job description")
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Job title")
        jd_file = st.file_uploader("Upload JD (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"], key="jd_upload")
    with col2:
        pasted_req = st.text_area("Or paste requirements text", height=150)

    if st.button("Add job", type="primary"):
        req_text = extract_text(jd_file) if jd_file else pasted_req
        if not title or not req_text.strip():
            st.error("Need a title and either an uploaded JD or pasted text.")
        else:
            row = run(
                "INSERT INTO jobs (title, requirements_text, jd_filename) VALUES (%s, %s, %s) RETURNING id",
                (title, req_text, jd_file.name if jd_file else None),
                fetchone=True,
            )
            if jd_file:
                vol_path = save_upload(jd_file, "job_descriptions", row["id"])
                if vol_path:
                    run("UPDATE jobs SET jd_volume_path = %s WHERE id = %s", (vol_path, row["id"]))
            st.success(f"Added job: {title}")

    st.divider()
    jobs = run("SELECT id, title, jd_filename, jd_volume_path, created_at FROM jobs ORDER BY created_at DESC", fetch=True)
    st.subheader("Existing jobs")
    st.dataframe(pd.DataFrame(jobs) if jobs else pd.DataFrame(columns=["id", "title", "jd_filename", "jd_volume_path"]),
                 use_container_width=True)

# ---------- Candidates ----------
with tab_candidates:
    st.subheader("Add a candidate")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name")
        email = st.text_input("Email")
        resume_file = st.file_uploader("Upload resume (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"], key="resume_upload")
    with col2:
        pasted_resume = st.text_area("Or paste resume text", height=150)

    if st.button("Add candidate", type="primary"):
        resume_text = extract_text(resume_file) if resume_file else pasted_resume
        if not name or not resume_text.strip():
            st.error("Need a name and either an uploaded resume or pasted text.")
        else:
            row = run(
                "INSERT INTO candidates (name, email, resume_text, resume_filename) VALUES (%s, %s, %s, %s) RETURNING id",
                (name, email, resume_text, resume_file.name if resume_file else None),
                fetchone=True,
            )
            if resume_file:
                vol_path = save_upload(resume_file, "resumes", row["id"])
                if vol_path:
                    run("UPDATE candidates SET resume_volume_path = %s WHERE id = %s", (vol_path, row["id"]))
            st.success(f"Added candidate: {name}")

    st.divider()
    candidates = run("SELECT id, name, email, resume_filename, resume_volume_path, created_at FROM candidates ORDER BY created_at DESC", fetch=True)
    st.subheader("Existing candidates")
    st.dataframe(pd.DataFrame(candidates) if candidates else pd.DataFrame(columns=["id", "name", "email", "resume_filename", "resume_volume_path"]),
                 use_container_width=True)

# ---------- Matching & Screening ----------
with tab_matching:
    jobs = run("SELECT * FROM jobs ORDER BY created_at DESC", fetch=True) or []
    candidates = run("SELECT * FROM candidates ORDER BY created_at DESC", fetch=True) or []

    if not jobs or not candidates:
        st.info("Add at least one job and one candidate first.")
    else:
        job_map = {j["title"]: j for j in jobs}
        cand_map = {c["name"]: c for c in candidates}

        c1, c2, c3 = st.columns([2, 2, 1])
        chosen_cand = c1.selectbox("Candidate", list(cand_map.keys()))
        chosen_job = c2.selectbox("Job", list(job_map.keys()))
        if c3.button("Run match", use_container_width=True):
            cand = cand_map[chosen_cand]
            job = job_map[chosen_job]
            score, matched = score_match(cand["resume_text"], job["requirements_text"])
            run(
                """INSERT INTO matches (candidate_id, job_id, score, matched_keywords)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (candidate_id, job_id)
                   DO UPDATE SET score = EXCLUDED.score, matched_keywords = EXCLUDED.matched_keywords,
                                 updated_at = now()""",
                (cand["id"], job["id"], score, ", ".join(matched)),
            )
            st.success(f"Match score: {score} — keywords: {', '.join(matched) or 'none'}")

    st.divider()
    st.subheader("All matches — update screening status")
    matches = run(
        """SELECT m.id, c.name AS candidate, j.title AS job, m.score, m.matched_keywords, m.stage
           FROM matches m
           JOIN candidates c ON c.id = m.candidate_id
           JOIN jobs j ON j.id = m.job_id
           ORDER BY m.score DESC""",
        fetch=True,
    )
    if matches:
        for m in matches:
            cols = st.columns([2, 2, 1, 3, 2])
            cols[0].write(m["candidate"])
            cols[1].write(m["job"])
            cols[2].write(f"{m['score']}")
            cols[3].write(m["matched_keywords"] or "")
            new_stage = cols[4].selectbox(
                "Stage", FUNNEL_STAGES, index=FUNNEL_STAGES.index(m["stage"]),
                key=f"stage_{m['id']}", label_visibility="collapsed"
            )
            if new_stage != m["stage"]:
                run("UPDATE matches SET stage = %s, updated_at = now() WHERE id = %s", (new_stage, m["id"]))
                st.rerun()
    else:
        st.write("No matches yet.")

# ---------- Hiring Funnel ----------
with tab_funnel:
    jobs = run("SELECT id, title FROM jobs ORDER BY created_at DESC", fetch=True) or []
    job_filter = st.selectbox("Filter by job (optional)", ["All jobs"] + [j["title"] for j in jobs])

    if job_filter == "All jobs":
        funnel_rows = run("SELECT stage, COUNT(*) AS n FROM matches GROUP BY stage", fetch=True) or []
    else:
        job_id = next(j["id"] for j in jobs if j["title"] == job_filter)
        funnel_rows = run(
            "SELECT stage, COUNT(*) AS n FROM matches WHERE job_id = %s GROUP BY stage",
            (job_id,), fetch=True,
        ) or []

    counts = {r["stage"]: r["n"] for r in funnel_rows}
    non_rejected_stages = [s for s in FUNNEL_STAGES if s != "rejected"]
    funnel_values = [counts.get(s, 0) for s in non_rejected_stages]

    st.subheader("Funnel (excludes rejected)")
    if sum(funnel_values) == 0:
        st.info("No candidates have been matched yet.")
    else:
        fig = go.Figure(go.Funnel(
            y=[s.capitalize() for s in non_rejected_stages],
            x=funnel_values,
            textinfo="value+percent initial",
        ))
        fig.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    rejected_count = counts.get("rejected", 0)
    st.metric("Rejected", rejected_count)

# ---------- Dashboard ----------
with tab_dashboard:
    total_jobs = run("SELECT COUNT(*) AS n FROM jobs", fetchone=True)["n"]
    total_candidates = run("SELECT COUNT(*) AS n FROM candidates", fetchone=True)["n"]
    total_matches = run("SELECT COUNT(*) AS n FROM matches", fetchone=True)["n"]
    avg_score_row = run("SELECT AVG(score) AS avg_score FROM matches", fetchone=True)
    avg_score = round(float(avg_score_row["avg_score"]), 1) if avg_score_row and avg_score_row["avg_score"] else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total jobs", total_jobs)
    c2.metric("Total candidates", total_candidates)
    c3.metric("Total matches", total_matches)
    c4.metric("Avg match score", avg_score)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Candidates per job")
        rows = run(
            """SELECT j.title, COUNT(m.id) AS candidate_count
               FROM jobs j LEFT JOIN matches m ON m.job_id = j.id
               GROUP BY j.title ORDER BY candidate_count DESC""",
            fetch=True,
        )
        if rows:
            df = pd.DataFrame(rows).set_index("title")
            st.bar_chart(df)
        else:
            st.write("No data yet.")

    with col2:
        st.subheader("Candidates by stage")
        rows = run("SELECT stage, COUNT(*) AS n FROM matches GROUP BY stage", fetch=True)
        if rows:
            df = pd.DataFrame(rows).set_index("stage")
            st.bar_chart(df)
        else:
            st.write("No data yet.")
