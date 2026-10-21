from app.services.matching import match_resume_to_job

def test_matching_is_explainable_and_deterministic():
    resume = "Built Python and FastAPI projects with PostgreSQL and LangGraph."
    skills = ["python", "fastapi", "postgresql", "langgraph"]
    jd = "Required skills: Python, FastAPI, LangGraph, Docker, SQL. Build and deploy a project."
    required = ["python", "fastapi", "langgraph", "docker", "sql"]
    a = match_resume_to_job(resume, skills, jd, required)
    b = match_resume_to_job(resume, skills, jd, required)
    assert a == b
    assert set(a["matched_skills"]) == {"python", "fastapi", "langgraph"}
    assert set(a["missing_skills"]) == {"docker", "sql"}
    assert 0 <= a["score"] <= 100
    assert "scoring_method" in a["evidence"]

def test_no_required_skills_does_not_crash():
    result = match_resume_to_job("A resume with projects", [], "General role", [])
    assert 0 <= result["score"] <= 100
