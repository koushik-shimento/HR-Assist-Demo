import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import pool, init_schema, run, FUNNEL_STAGES
from matching import score_match
from file_parsing import extract_text
from storage import save_upload

st.set_page_config(
    page_title="HR Assist | Talent Intelligence",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --blue: #2563eb;
        --blue-dark: #1746b5;
        --blue-soft: #eef5ff;
        --ink: #12213f;
        --muted: #71809e;
        --line: #e5ebf5;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f6f9ff; color: var(--ink); }
    .block-container { max-width: 1500px; padding: 1.25rem 2.2rem 3rem; }
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu, footer { visibility: hidden; }

    .app-header {
        display: flex; align-items: center; justify-content: space-between;
        gap: 24px; padding: 10px 4px 22px;
    }
    .brand { display: flex; align-items: center; gap: 12px; min-width: 220px; }
    .brand-mark {
        display: grid; place-items: center; width: 42px; height: 42px;
        color: white; font-size: 22px; border-radius: 13px;
        background: linear-gradient(135deg, #4385ff, #1856df);
        box-shadow: 0 8px 20px rgba(37,99,235,.28);
    }
    .brand-name { font-weight: 800; font-size: 20px; letter-spacing: -.5px; }
    .brand-name span { color: var(--blue); }
    .welcome { flex: 1; }
    .welcome h2 { margin: 0; font-size: 22px; letter-spacing: -.35px; }
    .welcome p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .profile {
        display: flex; align-items: center; gap: 10px; padding: 8px 12px;
        border: 1px solid var(--line); border-radius: 14px; background: white;
        box-shadow: 0 5px 16px rgba(30,64,175,.06);
    }
    .avatar { display:grid; place-items:center; width:34px; height:34px; border-radius:50%; background:#dbeafe; }
    .profile strong { display:block; font-size:12px; }
    .profile small { color:var(--muted); font-size:10px; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 7px; padding: 7px; border: 1px solid var(--line); border-radius: 15px;
        background: white; box-shadow: 0 8px 24px rgba(30,64,175,.06);
    }
    .stTabs [data-baseweb="tab"] {
        height: 43px; padding: 0 18px; border-radius: 10px; color: #52617e;
        font-size: 13px; font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background: var(--blue-soft); color: var(--blue) !important; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

    div[data-testid="stMetric"] {
        min-height: 128px; padding: 22px 24px; border: 1px solid var(--line);
        border-radius: 16px; background: white;
        box-shadow: 0 10px 25px rgba(30,64,175,.06);
        position: relative; overflow: hidden;
    }
    div[data-testid="stMetric"]:before {
        content: ''; position:absolute; inset: 0 auto 0 0; width:4px;
        background: linear-gradient(#60a5fa, #2563eb);
    }
    div[data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
    div[data-testid="stMetricValue"] { color: var(--ink); font-weight: 800; letter-spacing: -.8px; }

    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        border-color: var(--line) !important; border-radius: 16px !important;
        background: white; box-shadow: 0 8px 24px rgba(30,64,175,.05);
    }
    .stButton > button {
        border: 1px solid #c9d8f5; border-radius: 10px; font-weight: 650;
        color: var(--blue); background: white; min-height: 42px;
    }
    .stButton > button:hover { border-color: var(--blue); background: var(--blue-soft); color: var(--blue-dark); }
    .stButton > button[kind="primary"] {
        color: white; border: 0; background: linear-gradient(135deg, #3478f6, #1d56d8);
        box-shadow: 0 7px 16px rgba(37,99,235,.24);
    }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div,
    .stTextArea textarea, section[data-testid="stFileUploaderDropzone"] {
        border-color: #dce5f3; border-radius: 11px; background: #fbfdff;
    }
    h1, h2, h3 { color: var(--ink); letter-spacing: -.45px; }
    h3 { font-size: 17px !important; }
    hr { border-color: var(--line); }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 13px; overflow: hidden; }
    .section-note { color:var(--muted); font-size:13px; margin-top:-8px; margin-bottom:18px; }
    @media (max-width: 800px) {
        .block-container { padding: 1rem; }
        .app-header { align-items:flex-start; flex-wrap:wrap; }
        .welcome { order:3; flex-basis:100%; }
        .profile { display:none; }
        .stTabs [data-baseweb="tab"] { padding:0 10px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    init_schema()
except Exception as e:
    st.warning(f"Schema init: {e}")


st.markdown(
    """
    <div class="app-header">
      <div class="brand"><div class="brand-mark">♟</div><div class="brand-name">HR <span>Assist</span></div></div>
      <div class="welcome"><h2>Welcome back 👋</h2><p>Here’s what’s happening with your hiring pipeline today.</p></div>
      <div class="profile"><div class="avatar">👤</div><div><strong>HR Manager</strong><small>Talent team</small></div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_dashboard, tab_candidates, tab_jobs, tab_matching, tab_funnel = st.tabs(
    ["⌂  Dashboard", "♙  Candidates", "▣  Job Descriptions", "⌕  Matching & Screening", "▽  Hiring Funnel"]
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
    st.subheader("Add candidate(s)")
    st.caption(
        "Upload one resume with a name/email, or drop in many resumes at once "
        "for bulk import (filename becomes the candidate name; edit later)."
    )

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name (used only when uploading a single resume or pasting text)")
        email = st.text_input("Email (optional, single-upload only)")
        resume_files = st.file_uploader(
            "Upload resume(s) (PDF, DOCX, or TXT) — you can select multiple",
            type=["pdf", "docx", "txt"],
            key="resume_upload",
            accept_multiple_files=True,
        )
    with col2:
        pasted_resume = st.text_area(
            "Or paste a single resume as text (used only when no files uploaded)",
            height=150,
        )

    if st.button("Add candidate(s)", type="primary"):
        # ---- Case A: no files uploaded → single candidate from pasted text ----
        if not resume_files:
            resume_text = pasted_resume
            if not name or not resume_text.strip():
                st.error("Need a name and either an uploaded resume or pasted text.")
            else:
                row = run(
                    "INSERT INTO candidates (name, email, resume_text, resume_filename) "
                    "VALUES (%s, %s, %s, %s) RETURNING id",
                    (name, email, resume_text, None),
                    fetchone=True,
                )
                st.success(f"Added candidate: {name}")

        # ---- Case B: exactly 1 file → honor the name/email fields ----
        elif len(resume_files) == 1:
            f = resume_files[0]
            resume_text = extract_text(f)
            cand_name = name.strip() if name.strip() else Path(f.name).stem
            if not resume_text.strip():
                st.error(f"Couldn't extract any text from {f.name}.")
            else:
                row = run(
                    "INSERT INTO candidates (name, email, resume_text, resume_filename) "
                    "VALUES (%s, %s, %s, %s) RETURNING id",
                    (cand_name, email, resume_text, f.name),
                    fetchone=True,
                )
                vol_path = save_upload(f, "resumes", row["id"])
                if vol_path:
                    run(
                        "UPDATE candidates SET resume_volume_path = %s WHERE id = %s",
                        (vol_path, row["id"]),
                    )
                st.success(f"Added candidate: {cand_name}")

        # ---- Case C: bulk upload → one candidate per file, filename = name ----
        else:
            added, skipped = [], []
            progress = st.progress(0.0, text="Uploading resumes…")
            total = len(resume_files)

            for i, f in enumerate(resume_files, start=1):
                try:
                    resume_text = extract_text(f)
                    if not resume_text.strip():
                        skipped.append((f.name, "no text extracted"))
                        continue
                    cand_name = Path(f.name).stem
                    row = run(
                        "INSERT INTO candidates (name, email, resume_text, resume_filename) "
                        "VALUES (%s, %s, %s, %s) RETURNING id",
                        (cand_name, "", resume_text, f.name),
                        fetchone=True,
                    )
                    vol_path = save_upload(f, "resumes", row["id"])
                    if vol_path:
                        run(
                            "UPDATE candidates SET resume_volume_path = %s WHERE id = %s",
                            (vol_path, row["id"]),
                        )
                    added.append(cand_name)
                except Exception as e:
                    skipped.append((f.name, str(e)))
                finally:
                    progress.progress(i / total, text=f"Processed {i}/{total}")

            progress.empty()
            if added:
                st.success(f"Added {len(added)} candidate(s): {', '.join(added)}")
            if skipped:
                with st.expander(f"{len(skipped)} file(s) skipped — click for details"):
                    for fname, reason in skipped:
                        st.write(f"• **{fname}** — {reason}")

    st.divider()
    candidates = run(
        "SELECT id, name, email, resume_filename, resume_volume_path, created_at "
        "FROM candidates ORDER BY created_at DESC",
        fetch=True,
    )
    st.subheader("Existing candidates")
    st.dataframe(
        pd.DataFrame(candidates)
        if candidates
        else pd.DataFrame(columns=["id", "name", "email", "resume_filename", "resume_volume_path"]),
        use_container_width=True,
    )

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
            marker={"color": ["#2563eb", "#4f8ef7", "#60a5fa", "#38bdf8", "#22c3b6", "#7c5ce5"]},
            connector={"line": {"color": "#dbe7fa", "width": 1}},
        ))
        fig.update_layout(
            margin=dict(t=10, b=10), height=430, paper_bgcolor="rgba(0,0,0,0)",
            font={"family": "Inter", "color": "#52617e"},
        )
        st.plotly_chart(fig, use_container_width=True)

    rejected_count = counts.get("rejected", 0)
    st.metric("Rejected", rejected_count)

# ---------- Dashboard ----------
with tab_dashboard:
    st.subheader("Overview")
    st.markdown('<p class="section-note">A live snapshot of recruiting performance and candidate flow.</p>', unsafe_allow_html=True)
    total_jobs = run("SELECT COUNT(*) AS n FROM jobs", fetchone=True)["n"]
    total_candidates = run("SELECT COUNT(*) AS n FROM candidates", fetchone=True)["n"]
    total_matches = run("SELECT COUNT(*) AS n FROM matches", fetchone=True)["n"]
    avg_score_row = run("SELECT AVG(score) AS avg_score FROM matches", fetchone=True)
    avg_score = round(float(avg_score_row["avg_score"]), 1) if avg_score_row and avg_score_row["avg_score"] else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Open positions", total_jobs, help="Jobs currently in the system")
    c2.metric("Total candidates", total_candidates, help="All candidate profiles")
    c3.metric("Candidate matches", total_matches, help="Completed job matches")
    c4.metric("Average match score", f"{avg_score}%", help="Average relevance across all matches")

    st.divider()
    col1, col2 = st.columns(2)

    with col1.container(border=True):
        st.subheader("Candidates per job")
        rows = run(
            """SELECT j.title, COUNT(m.id) AS candidate_count
               FROM jobs j LEFT JOIN matches m ON m.job_id = j.id
               GROUP BY j.title ORDER BY candidate_count DESC""",
            fetch=True,
        )
        if rows:
            df = pd.DataFrame(rows)
            fig = go.Figure(go.Bar(
                x=df["candidate_count"], y=df["title"], orientation="h",
                marker={"color": "#3478f6", "cornerradius": 6},
                hovertemplate="%{y}: %{x} candidates<extra></extra>",
            ))
            fig.update_layout(
                height=350, margin=dict(l=10, r=15, t=10, b=20),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"family": "Inter", "color": "#52617e"},
                xaxis={"showgrid": True, "gridcolor": "#edf2fa", "title": None},
                yaxis={"showgrid": False, "title": None, "autorange": "reversed"},
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Add a job and run a match to populate this chart.")

    with col2.container(border=True):
        st.subheader("Candidates by stage")
        rows = run("SELECT stage, COUNT(*) AS n FROM matches GROUP BY stage", fetch=True)
        if rows:
            df = pd.DataFrame(rows)
            palette = ["#2563eb", "#60a5fa", "#38bdf8", "#22c3b6", "#7c5ce5", "#f59e0b", "#94a3b8"]
            fig = go.Figure(go.Pie(
                labels=df["stage"].str.title(), values=df["n"], hole=.62,
                marker={"colors": palette, "line": {"color": "white", "width": 3}},
                textinfo="percent", hovertemplate="%{label}: %{value}<extra></extra>",
            ))
            fig.update_layout(
                height=350, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", font={"family": "Inter", "color": "#52617e"},
                legend={"orientation": "h", "y": -.05, "xanchor": "center", "x": .5},
                annotations=[{"text": f"<b>{total_matches}</b><br><span style='font-size:11px'>Matches</span>", "x": .5, "y": .5, "showarrow": False}],
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Candidate stages will appear after the first match.")
