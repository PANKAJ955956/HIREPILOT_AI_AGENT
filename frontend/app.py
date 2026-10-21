import os
import requests
import pandas as pd
import streamlit as st

API = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
st.set_page_config(page_title="HirePilot AI", page_icon="🧭", layout="wide")
st.markdown("""<style>.block-container{padding-top:1.8rem}.hero{padding:1.4rem;border-radius:18px;background:linear-gradient(120deg,#10243a,#245c75);color:white}.small{color:#6b7280;font-size:.9rem}</style>""", unsafe_allow_html=True)

def api(method, path, **kwargs):
    try:
        response = requests.request(method, f"{API}{path}", timeout=120, **kwargs)
        if response.ok:
            return response.json()
        try: detail = response.json().get("detail", response.text)
        except Exception: detail = response.text
        st.error(f"API error ({response.status_code}): {detail}")
    except requests.RequestException as exc:
        st.error(f"Cannot reach API at {API}. Start the backend and check API_BASE_URL. Details: {exc}")
    return None

st.markdown('<div class="hero"><h1>🧭 HirePilot AI</h1><p>Agentic Recruitment & Career Copilot</p><p>Resume intelligence · Explainable matching · Interview coach · Career roadmap · Application tracking</p></div>', unsafe_allow_html=True)
health = api("GET", "/api/health")
if health:
    st.caption(f"API: online · Gemini configured: {'yes' if health.get('llm_configured') else 'no — set GEMINI_API_KEY'}")

page = st.sidebar.radio("Workspace", ["Overview", "Resume Analyzer", "Jobs & Matching", "Interview Coach", "Career Roadmap", "Applications", "Semantic Search"])
if page == "Overview":
    data = api("GET", "/api/analytics") or {}
    cols = st.columns(4)
    for col, label, key in zip(cols, ["Candidates", "Jobs", "Match reports", "Applications"], ["candidate_count", "job_count", "match_count", "application_count"]): col.metric(label, data.get(key, 0))
    st.subheader("Application pipeline")
    statuses = data.get("applications_by_status", {})
    if statuses: st.bar_chart(pd.DataFrame({"Applications": statuses}).sort_index())
    else: st.info("No tracked applications yet. Upload a resume and add a job to start.")
    st.subheader("Recent match reports")
    matches = api("GET", "/api/matches")
    if matches: st.dataframe(pd.DataFrame(matches)[["candidate_name", "job_title", "company", "score", "matched_skills", "missing_skills"]], use_container_width=True, hide_index=True)
    st.caption("Match scores are explainable estimates, not hiring decisions. Review candidate evidence manually.")

elif page == "Resume Analyzer":
    st.subheader("Upload and parse a resume")
    file = st.file_uploader("Resume file", type=["pdf", "docx", "txt"])
    if st.button("Analyze resume", type="primary", disabled=file is None):
        with st.spinner("Extracting resume text and skills..."):
            result = api("POST", "/api/candidates/upload", files={"file": (file.name, file.getvalue(), file.type or "application/octet-stream")})
        if result:
            st.success(f"Candidate created · ID {result['id']}")
            a,b = st.columns(2); a.write("**Name**"); a.write(result["full_name"]); b.write("**Email**"); b.write(result.get("email") or "Not detected")
            st.write("**Detected skills**"); st.write(", ".join(result["skills"]) or "No known skills detected. Check the extracted resume text manually.")
            st.write("**Education evidence**"); st.write("
".join(f"- {x}" for x in result["education"]) or "No education lines detected.")
            with st.expander("Show full extracted experience summary"): st.text(result.get("experience_summary", ""))
    st.subheader("Saved candidates")
    rows = api("GET", "/api/candidates")
    if rows: st.dataframe(pd.DataFrame(rows)[["id", "full_name", "email", "resume_filename", "skills"]], use_container_width=True, hide_index=True)

elif page == "Jobs & Matching":
    st.subheader("Add a job description")
    with st.form("job_form"):
        title = st.text_input("Role title", placeholder="Generative AI Engineer")
        company = st.text_input("Company", placeholder="Company name")
        location = st.text_input("Location", placeholder="Noida / Remote")
        url = st.text_input("Job URL (optional)")
        desc = st.text_area("Full job description", height=180)
        save = st.form_submit_button("Save job", type="primary")
    if save:
        if len(desc.strip()) < 20: st.warning("Please paste the full job description (at least 20 characters).")
        else:
            result = api("POST", "/api/jobs", json={"title": title, "company": company or "Not specified", "location": location or "Not specified", "source_url": url or None, "description": desc})
            if result: st.success(f"Saved job #{result['id']} · extracted {len(result['required_skills'])} skill terms")
    candidates = api("GET", "/api/candidates") or []; jobs = api("GET", "/api/jobs") or []
    st.subheader("Run explainable resume–job matching")
    if candidates and jobs:
        c_map = {f"#{x['id']} {x['full_name']} — {x['resume_filename']}": x['id'] for x in candidates}
        j_map = {f"#{x['id']} {x['title']} — {x['company']}": x['id'] for x in jobs}
        c1,c2 = st.columns(2); selected_c = c1.selectbox("Candidate", list(c_map)); selected_j = c2.selectbox("Job", list(j_map))
        if st.button("Run match analysis", type="primary"):
            with st.spinner("Calculating evidence-based score and requesting Gemini explanation..."):
                result = api("POST", "/api/matches", json={"candidate_id": c_map[selected_c], "job_id": j_map[selected_j]})
            if result:
                st.metric("Explainable fit estimate", f"{result['score']}/100")
                a,b = st.columns(2); a.write("**Matched skills**"); a.write(result["matched_skills"] or ["No required skills matched"]); b.write("**Missing skills**"); b.write(result["missing_skills"] or ["No missing skills identified by extractor"])
                st.json(result["evidence"])
                st.markdown("**Gemini analysis**"); st.markdown(result["ai_explanation"])
                st.caption("This is a decision-support tool. It does not assess protected characteristics and must not make autonomous hiring decisions.")
    else: st.info("Add at least one candidate and one job before matching.")
    matches = api("GET", "/api/matches")
    if matches: st.subheader("Saved match reports"); st.dataframe(pd.DataFrame(matches)[["id", "candidate_name", "job_title", "company", "score", "created_at"]], use_container_width=True, hide_index=True)

elif page == "Interview Coach":
    st.subheader("Generate a personalized mock interview")
    candidates = api("GET", "/api/candidates") or []; jobs = api("GET", "/api/jobs") or []
    with st.form("interview_form"):
        role = st.text_input("Target role", "AI Engineer")
        level = st.selectbox("Seniority", ["entry", "mid", "senior"])
        count = st.slider("Question count", 3, 20, 8)
        candidate_choice = st.selectbox("Candidate context (optional)", ["None"] + [f"#{x['id']} {x['full_name']}" for x in candidates])
        job_choice = st.selectbox("Job context (optional)", ["None"] + [f"#{x['id']} {x['title']} — {x['company']}" for x in jobs])
        go = st.form_submit_button("Generate interview", type="primary")
    if go:
        c_id = int(candidate_choice.split(" ")[0][1:]) if candidate_choice != "None" else None
        j_id = int(job_choice.split(" ")[0][1:]) if job_choice != "None" else None
        with st.spinner("Gemini is preparing role-specific questions..."):
            result = api("POST", "/api/interviews", json={"role": role, "level": level, "question_count": count, "candidate_id": c_id, "job_id": j_id})
        if result: st.markdown(result["questions_markdown"])

elif page == "Career Roadmap":
    candidates = api("GET", "/api/candidates") or []
    if not candidates: st.info("Upload a resume first to personalize the roadmap.")
    else:
        options = {f"#{x['id']} {x['full_name']}": x['id'] for x in candidates}
        chosen = st.selectbox("Candidate", list(options)); target = st.text_input("Target role", "Agentic AI Engineer"); days = st.slider("Roadmap duration (days)", 7, 180, 30)
        if st.button("Generate career roadmap", type="primary"):
            with st.spinner("Analyzing current skills and generating a plan..."):
                result = api("POST", "/api/career-roadmap", json={"candidate_id": options[chosen], "target_role": target, "timeframe_days": days})
            if result: st.markdown(result["roadmap_markdown"])

elif page == "Applications":
    st.subheader("Application tracker")
    candidates = api("GET", "/api/candidates") or []; jobs = api("GET", "/api/jobs") or []
    if candidates and jobs:
        c_map = {f"#{x['id']} {x['full_name']}": x['id'] for x in candidates}; j_map = {f"#{x['id']} {x['title']} — {x['company']}": x['id'] for x in jobs}
        with st.form("application_form"):
            c = st.selectbox("Candidate", list(c_map)); j = st.selectbox("Job", list(j_map)); status = st.selectbox("Status", ["saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn"]); notes = st.text_area("Notes")
            add = st.form_submit_button("Add tracker entry")
        if add:
            result = api("POST", "/api/applications", json={"candidate_id": c_map[c], "job_id": j_map[j], "status": status, "notes": notes})
            if result: st.success("Application tracker entry saved.")
    rows = api("GET", "/api/applications") or []
    if rows:
        st.dataframe(pd.DataFrame(rows)[["id", "candidate_name", "job_title", "company", "status", "notes", "updated_at"]], use_container_width=True, hide_index=True)
        st.markdown("**Update status**")
        app_map = {f"#{x['id']} {x['candidate_name']} → {x['job_title']} ({x['status']})": x['id'] for x in rows}
        chosen = st.selectbox("Application", list(app_map)); new_status = st.selectbox("New status", ["saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn"]); new_notes = st.text_input("Replace notes (optional)")
        if st.button("Update application"):
            payload = {"status": new_status}
            if new_notes: payload["notes"] = new_notes
            result = api("PATCH", f"/api/applications/{app_map[chosen]}", json=payload)
            if result: st.success("Application updated."); st.rerun()
    else: st.info("No applications tracked yet.")

elif page == "Semantic Search":
    st.subheader("Search indexed resumes and job descriptions")
    q = st.text_input("Search query", placeholder="Python, RAG, agentic workflows")
    if st.button("Search documents", type="primary", disabled=len(q.strip()) < 2):
        result = api("GET", "/api/search", params={"q": q, "limit": 6})
        if result:
            if result["results"]:
                for item in result["results"]:
                    st.markdown(f"**{item['metadata'].get('type','document').title()} · {item['metadata'].get('candidate_id', item['metadata'].get('job_id',''))}**")
                    st.write(item["text"])
                    st.caption(f"Metadata: {item['metadata']}")
            else: st.info("No indexed documents yet. Upload a resume or save a job first.")
st.divider()
st.caption("HirePilot AI · Gemini-powered assistance · PostgreSQL persistence · ChromaDB semantic search. Keep a human in the loop for recruitment decisions.")
