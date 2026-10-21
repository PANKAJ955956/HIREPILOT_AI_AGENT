from app.services.resume_parser import extract_text, extract_skills
import pytest

def test_txt_resume_parsing():
    text = extract_text("resume.txt", b"Jane Doe\nPython engineer with FastAPI, PostgreSQL and LangGraph project experience.")
    assert "Python" in text
    assert "fastapi" in extract_skills(text)

def test_unsupported_file():
    with pytest.raises(ValueError): extract_text("resume.png", b"not a resume")
