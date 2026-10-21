from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.database import get_db
from app.config import settings
from app.models.entities import Candidate, Job, MatchReport, Application, InterviewSession
from app.schemas import JobCreate, JobOut, CandidateOut, MatchRequest, ApplicationCreate, ApplicationUpdate, InterviewRequest, CareerRequest
from app.services.resume_parser import extract_text, extract_profile, extract_skills
from app.services.matching import match_resume_to_job
from app.services.vector_store import index_document, search_documents
from app.agents.workflows import run_match_explanation, run_content_agent

router = APIRouter(prefix="/api")

@router.get("/health")
def health():
    return {"status": "ok", "service": "HirePilot AI", "llm_configured": bool(settings.gemini_api_key)}

@router.post("/candidates/upload", response_model=CandidateOut)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    allowed = {".pdf", ".docx", ".txt"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed: raise HTTPException(400, "Upload a PDF, DOCX, or TXT resume.")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")
    try:
        text = extract_text(file.filename or "resume", content)
        profile = extract_profile(text, file.filename or "resume")
    except ValueError as exc: raise HTTPException(422, str(exc))
    candidate = Candidate(**profile)
    db.add(candidate); db.commit(); db.refresh(candidate)
    try: index_document(f"candidate-{candidate.id}", text, {"type": "resume", "candidate_id": candidate.id})
    except Exception: pass  # Core workflow remains available if optional vector index is temporarily unavailable.
    return candidate

@router.get("/candidates", response_model=list[CandidateOut])
def list_candidates(db: Session = Depends(get_db), limit: int = Query(default=100, ge=1, le=500)):
    return list(db.scalars(select(Candidate).order_by(Candidate.created_at.desc()).limit(limit)))

@router.get("/candidates/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    obj = db.get(Candidate, candidate_id)
    if not obj: raise HTTPException(404, "Candidate not found")
    return obj

@router.post("/jobs", response_model=JobOut)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    job = Job(**payload.model_dump(), required_skills=extract_skills(payload.description))
    db.add(job); db.commit(); db.refresh(job)
    try: index_document(f"job-{job.id}", payload.description, {"type": "job", "job_id": job.id})
    except Exception: pass
    return job

@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), limit: int = Query(default=100, ge=1, le=500)):
    return list(db.scalars(select(Job).order_by(Job.created_at.desc()).limit(limit)))

@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    obj = db.get(Job, job_id)
    if not obj: raise HTTPException(404, "Job not found")
    return obj

@router.post("/matches")
def create_match(payload: MatchRequest, db: Session = Depends(get_db)):
    candidate, job = db.get(Candidate, payload.candidate_id), db.get(Job, payload.job_id)
    if not candidate or not job: raise HTTPException(404, "Candidate or job not found")
    metrics = match_resume_to_job(candidate.resume_text, candidate.skills, job.description, job.required_skills)
    try:
        explanation = run_match_explanation({"resume_text": candidate.resume_text, "job_description": job.description, **metrics})
    except Exception as exc:
        # Do not fabricate an AI explanation. The deterministic report is still useful, and LLM failure is explicit.
        explanation = f"AI explanation unavailable: {type(exc).__name__}. Configure GEMINI_API_KEY and verify provider connectivity. The score and skill coverage are calculated locally from resume/job text."
    report = MatchReport(candidate_id=candidate.id, job_id=job.id, score=metrics["score"], matched_skills=metrics["matched_skills"], missing_skills=metrics["missing_skills"], evidence=metrics["evidence"], ai_explanation=explanation)
    db.add(report); db.commit(); db.refresh(report)
    return {"id": report.id, "candidate_id": candidate.id, "job_id": job.id, **metrics, "ai_explanation": report.ai_explanation, "created_at": report.created_at}

@router.get("/matches")
def list_matches(db: Session = Depends(get_db), limit: int = Query(default=100, ge=1, le=500)):
    rows = db.scalars(select(MatchReport).order_by(MatchReport.created_at.desc()).limit(limit)).all()
    return [{"id": x.id, "candidate_id": x.candidate_id, "job_id": x.job_id, "candidate_name": x.candidate.full_name, "job_title": x.job.title, "company": x.job.company, "score": x.score, "matched_skills": x.matched_skills, "missing_skills": x.missing_skills, "evidence": x.evidence, "ai_explanation": x.ai_explanation, "created_at": x.created_at} for x in rows]

@router.post("/interviews")
def generate_interview(payload: InterviewRequest, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, payload.candidate_id) if payload.candidate_id else None
    job = db.get(Job, payload.job_id) if payload.job_id else None
    if payload.candidate_id and not candidate: raise HTTPException(404, "Candidate not found")
    if payload.job_id and not job: raise HTTPException(404, "Job not found")
    context = f"""Role: {payload.role}
Level: {payload.level}
Candidate skills: {candidate.skills if candidate else 'not provided'}
Resume: {candidate.resume_text[:5000] if candidate else 'not provided'}
Job description: {job.description[:4000] if job else 'not provided'}
Create exactly {payload.question_count} numbered interview questions with a mix of fundamentals, practical scenarios, and role-relevant problem solving. For each include what a strong answer should cover. Return Markdown."""
    try: result = run_content_agent("Generate a role-specific mock interview", context)
    except Exception as exc: raise HTTPException(503, f"Gemini generation failed ({type(exc).__name__}). Check GEMINI_API_KEY, model access, and network connectivity.")
    session = InterviewSession(candidate_id=candidate.id if candidate else None, role=payload.role, questions=[{"content": result}], feedback={})
    db.add(session); db.commit(); db.refresh(session)
    return {"id": session.id, "role": payload.role, "questions_markdown": result, "created_at": session.created_at}

@router.post("/career-roadmap")
def career_roadmap(payload: CareerRequest, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate: raise HTTPException(404, "Candidate not found")
    context = f"""Target role: {payload.target_role}
Timeframe: {payload.timeframe_days} days
Current skills: {candidate.skills}
Resume: {candidate.resume_text[:7000]}
Create a realistic week-by-week plan. Include priority skill gaps, hands-on deliverables, evaluation criteria, and portfolio project milestones. Clearly label assumptions and do not claim a course or job is guaranteed."""
    try: result = run_content_agent("Create a personalized career skill-gap analysis and learning roadmap", context)
    except Exception as exc: raise HTTPException(503, f"Gemini generation failed ({type(exc).__name__}). Check GEMINI_API_KEY, model access, and network connectivity.")
    return {"candidate_id": candidate.id, "target_role": payload.target_role, "timeframe_days": payload.timeframe_days, "current_skills": candidate.skills, "roadmap_markdown": result}

@router.post("/applications")
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    if not db.get(Candidate, payload.candidate_id) or not db.get(Job, payload.job_id): raise HTTPException(404, "Candidate or job not found")
    exists = db.scalar(select(Application).where(Application.candidate_id == payload.candidate_id, Application.job_id == payload.job_id))
    if exists: raise HTTPException(409, "An application tracker entry already exists for this candidate and job")
    app = Application(**payload.model_dump(), applied_at=datetime.now(timezone.utc) if payload.status != "saved" else None)
    db.add(app); db.commit(); db.refresh(app)
    return serialize_application(app)

def serialize_application(x):
    return {"id": x.id, "candidate_id": x.candidate_id, "candidate_name": x.candidate.full_name, "job_id": x.job_id, "job_title": x.job.title, "company": x.job.company, "status": x.status, "notes": x.notes, "applied_at": x.applied_at, "updated_at": x.updated_at}

@router.get("/applications")
def list_applications(db: Session = Depends(get_db)):
    rows = db.scalars(select(Application).order_by(Application.updated_at.desc())).all()
    return [serialize_application(x) for x in rows]

@router.patch("/applications/{application_id}")
def update_application(application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)):
    app = db.get(Application, application_id)
    if not app: raise HTTPException(404, "Application not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items(): setattr(app, key, value)
    if app.status != "saved" and app.applied_at is None: app.applied_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(app)
    return serialize_application(app)

@router.delete("/applications/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, application_id)
    if not app: raise HTTPException(404, "Application not found")
    db.delete(app); db.commit(); return {"deleted": True, "id": application_id}

@router.get("/search")
def semantic_search(q: str = Query(min_length=2), limit: int = Query(default=4, ge=1, le=10)):
    try: return {"query": q, "results": search_documents(q, limit)}
    except Exception as exc: raise HTTPException(503, f"Vector search unavailable: {type(exc).__name__}")

@router.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    statuses = db.execute(select(Application.status, func.count(Application.id)).group_by(Application.status)).all()
    return {"candidate_count": (db.scalar(select(func.count(Candidate.id))) or 0), "job_count": (db.scalar(select(func.count(Job.id))) or 0), "match_count": (db.scalar(select(func.count(MatchReport.id))) or 0), "application_count": (db.scalar(select(func.count(Application.id))) or 0), "applications_by_status": {s: n for s, n in statuses}}
