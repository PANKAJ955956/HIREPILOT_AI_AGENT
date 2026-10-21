from pydantic import BaseModel, Field, HttpUrl
from typing import Literal

class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=250)
    company: str = "Not specified"
    location: str = "Not specified"
    source_url: str | None = None
    description: str = Field(min_length=20)

class JobOut(BaseModel):
    id: int; title: str; company: str; location: str; source_url: str | None; description: str; required_skills: list
    model_config = {"from_attributes": True}

class CandidateOut(BaseModel):
    id: int; full_name: str; email: str | None; resume_filename: str; skills: list; education: list; experience_summary: str
    model_config = {"from_attributes": True}

class MatchRequest(BaseModel):
    candidate_id: int
    job_id: int

class ApplicationCreate(BaseModel):
    candidate_id: int
    job_id: int
    status: Literal["saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn"] = "saved"
    notes: str = ""

class ApplicationUpdate(BaseModel):
    status: Literal["saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn"] | None = None
    notes: str | None = None

class InterviewRequest(BaseModel):
    role: str = Field(min_length=2, max_length=250)
    candidate_id: int | None = None
    job_id: int | None = None
    question_count: int = Field(default=8, ge=3, le=20)
    level: Literal["entry", "mid", "senior"] = "entry"

class CareerRequest(BaseModel):
    target_role: str = Field(min_length=2, max_length=250)
    candidate_id: int
    timeframe_days: int = Field(default=30, ge=7, le=180)
