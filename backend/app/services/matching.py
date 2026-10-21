import re
from app.services.resume_parser import extract_skills

def normalize(skill: str) -> str:
    return re.sub(r"\s+", " ", skill.lower().strip())

def match_resume_to_job(resume_text: str, candidate_skills: list[str], job_description: str, required_skills: list[str]) -> dict:
    # Deterministic, explainable score. LLM prose is separate and cannot change the score.
    jd_skills = sorted(set(normalize(x) for x in (required_skills or extract_skills(job_description))))
    candidate = set(normalize(x) for x in candidate_skills)
    jd_lower = job_description.lower()
    matched = [s for s in jd_skills if s in candidate or re.search(r"(?<![a-z0-9])" + re.escape(s) + r"(?![a-z0-9])", resume_text.lower())]
    missing = [s for s in jd_skills if s not in matched]
    skill_score = len(matched) / len(jd_skills) * 75 if jd_skills else 0
    # Evidence-based experience signal, capped; no protected characteristics are used.
    evidence_terms = ["project", "internship", "experience", "deployed", "built", "developed", "implemented"]
    evidence_hits = sum(1 for term in evidence_terms if term in resume_text.lower() and term in jd_lower)
    evidence_score = min(15, evidence_hits * 3)
    keyword_overlap = len(set(re.findall(r"[a-z][a-z0-9+#.-]{2,}", jd_lower)) & set(re.findall(r"[a-z][a-z0-9+#.-]{2,}", resume_text.lower())))
    context_score = min(10, keyword_overlap / max(1, min(50, len(jd_lower.split()))) * 50)
    score = round(min(100, skill_score + evidence_score + context_score), 1)
    return {"score": score, "matched_skills": matched, "missing_skills": missing, "evidence": {"skill_coverage_percent": round(100*len(matched)/len(jd_skills), 1) if jd_skills else None, "matched_skill_count": len(matched), "required_skill_count": len(jd_skills), "experience_evidence_hits": evidence_hits, "context_keyword_overlap_count": keyword_overlap, "scoring_method": "75% skill coverage + up to 15 points for shared project/experience evidence + up to 10 points for keyword overlap. This is an assistive estimate, not a hiring decision."}}
