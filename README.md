# HirePilot AI — Agentic Recruitment & Career Copilot

A portfolio-grade, human-in-the-loop recruitment assistant built with **FastAPI, LangGraph, Gemini, PostgreSQL, ChromaDB, and Streamlit**. It provides resume parsing, explainable resume-to-job matching, interview generation, personalized career roadmaps, semantic document search, and persistent application tracking.

> Important: this is decision-support software, not an automated hiring decision-maker. Scores are deterministic estimates based on explicit text evidence; recruiters must review the source material. Never use protected characteristics to rank candidates.

## Features

- PDF, DOCX and TXT resume extraction; skill, education and experience evidence parsing.
- Save job descriptions and extract recognizable skill terms.
- Explainable match score: up to 75 points from skill coverage, 15 from shared project/experience evidence, and 10 from contextual keyword overlap. The method and counts are returned with every report.
- LangGraph workflow calls Gemini to produce a grounded explanation. A provider failure is surfaced explicitly; the app does not fabricate an AI response.
- Gemini-powered interview questions and skill-gap learning roadmaps.
- PostgreSQL-backed candidates, jobs, match reports, interview sessions and application tracker.
- ChromaDB persistent semantic search for resume/job text chunks.
- Streamlit dashboard plus documented REST API at `/docs`.
- Unit tests for deterministic matching and resume text parsing.

## Architecture

```text
Streamlit dashboard
       | REST / JSON
FastAPI routes and validation
       |-------------------------------|
PostgreSQL / SQLAlchemy       LangGraph workflows
       |                       | Gemini API
Candidates, jobs, matches     | explanations / content
Applications, interviews     ChromaDB semantic index
```

## Prerequisites

- Python 3.11+ (Python 3.12 recommended)
- PostgreSQL 15+ (or Docker Desktop)
- Google AI Studio Gemini API key
- Git (optional)

## Quick start with Docker Compose (recommended)

1. Copy `.env.example` to `.env` and add your key:

   ```bash
   cp .env.example .env
   ```

   Set `GEMINI_API_KEY` to your Google AI Studio API key. The compose file uses a local PostgreSQL service with the development credentials shown in the compose configuration. Change these credentials before any shared or cloud deployment.

2. Start all services from the repository root:

   ```bash
   docker compose up --build
   ```

3. Open:
   - Dashboard: http://localhost:8501
   - API docs: http://localhost:8000/docs
   - Health: http://localhost:8000/api/health

The first build may take several minutes because ChromaDB and document-processing dependencies are installed. `docker compose down` stops services; `docker compose down -v` also deletes the local PostgreSQL volume.

## Local development

### 1. Start PostgreSQL

Start PostgreSQL locally or use only the database service from Compose:

```bash
docker compose up -d db
```

Copy `.env.example` to `.env`. For local Python execution, use this `DATABASE_URL`:

```text
postgresql+psycopg://hirepilot:change_me@localhost:5432/hirepilot
```

Change the password to match your local database configuration.

### 2. Install backend dependencies

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

### 3. Run the API

From the repository root:

```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### 4. Run the dashboard in another terminal

```bash
pip install -r frontend/requirements.txt
streamlit run frontend/app.py --server.port 8501
```

If the dashboard cannot reach the API, set `API_BASE_URL=http://localhost:8000`. This is the default for local development. In Docker Compose, the dashboard is configured to use `http://api:8000` internally.

## Environment variables

| Variable | Purpose | Example |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio key; required for AI-generated explanations, interviews and roadmaps | secret value |
| `GEMINI_MODEL` | Gemini model name enabled for your account | `gemini-2.5-flash` |
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection | `postgresql+psycopg://user:pass@host:5432/db` |
| `CHROMA_PERSIST_DIR` | Local persistent Chroma index path | `./data/chroma` |
| `UPLOAD_DIR` | Directory for future managed uploads; current upload processing is in-memory | `./data/uploads` |
| `MAX_UPLOAD_MB` | Upload size cap | `10` |
| `CORS_ORIGINS` | Comma-separated browser origins | `http://localhost:8501` |
| `APP_ENV` | Environment label | `development` |

Never commit `.env`, expose a Gemini key in frontend code, or use development database credentials in production.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | API status and whether Gemini key is configured |
| `POST` | `/api/candidates/upload` | Upload PDF/DOCX/TXT resume as multipart `file` |
| `GET` | `/api/candidates` | List parsed candidate profiles |
| `GET` | `/api/candidates/{id}` | Get candidate profile |
| `POST` | `/api/jobs` | Save job title, company, location, URL and description |
| `GET` | `/api/jobs` | List saved jobs |
| `POST` | `/api/matches` | Generate and persist explainable candidate/job match |
| `GET` | `/api/matches` | List saved match reports |
| `POST` | `/api/interviews` | Generate a role-specific interview using Gemini |
| `POST` | `/api/career-roadmap` | Generate a personalized skill-gap plan using Gemini |
| `POST` | `/api/applications` | Create an application tracker entry |
| `GET` | `/api/applications` | List application tracker entries |
| `PATCH` | `/api/applications/{id}` | Update status/notes |
| `DELETE` | `/api/applications/{id}` | Delete tracker entry |
| `GET` | `/api/search?q=...` | Semantic search over indexed resume/job chunks |
| `GET` | `/api/analytics` | Dashboard counts and application status distribution |

### Example requests

Create a job:

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"title":"AI Engineer","company":"Example Co","location":"Noida","description":"Required: Python, FastAPI, LangGraph, SQL and RAG. Build reliable AI systems."}'
```

Upload a resume:

```bash
curl -X POST http://localhost:8000/api/candidates/upload \
  -F 'file=@./resume.pdf'
```

Run a match (replace IDs with values returned by the API):

```bash
curl -X POST http://localhost:8000/api/matches \
  -H 'Content-Type: application/json' \
  -d '{"candidate_id":1,"job_id":1}'
```

## Tests

Install test dependencies and run from repository root:

```bash
pip install pytest
pytest -q
```

Tests cover resume parsing and deterministic match calculations. Gemini calls are intentionally not mocked as successful in production routes: when provider configuration/network fails, the relevant endpoint returns an explicit error or a clearly marked unavailable explanation.

## Cloud deployment

### Recommended topology

- API: Render, Railway, Fly.io, or AWS App Runner/container service.
- Database: managed PostgreSQL with SSL and backups.
- Dashboard: Streamlit Community Cloud or a container service.
- ChromaDB: for a single-instance deployment, mount a persistent disk at `CHROMA_PERSIST_DIR`. For multi-replica/production use, move to a managed vector store or PostgreSQL pgvector and implement authenticated access.

### Deploy checklist

1. Push this repository to a private/public Git repository after checking for secrets.
2. Provision managed PostgreSQL and copy its connection string. For providers requiring SSL, append the provider-required SSL parameters (for example `?sslmode=require`) and ensure the driver/host supports them.
3. Deploy the backend using `backend/Dockerfile`; set `DATABASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `CHROMA_PERSIST_DIR`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `CORS_ORIGINS`, and `APP_ENV` in the host's secret/environment settings.
4. Attach persistent disk storage for ChromaDB if retaining the local Chroma index. Do not rely on ephemeral filesystem storage for persistent vector data.
5. Deploy the Streamlit container using `frontend/Dockerfile`; set `API_BASE_URL` to the public HTTPS backend URL. Set `CORS_ORIGINS` for any browser-based frontend origins; Streamlit server-to-server calls are not subject to browser CORS in the same way.
6. Verify `/api/health`, `/docs`, upload, matching, interview generation, and application status update.
7. Enable TLS, access control, database backups, rate limits, logging, upload retention policy and privacy notice before accepting real candidate data.

**Production gaps to address before public launch:** add authentication/authorization and tenant isolation, virus scanning, audit logs, PII retention/deletion workflows, API rate limiting, database migrations (Alembic), OCR for scanned resumes, structured Gemini output validation, background jobs for long-running tasks, and automated monitoring. Do not expose candidate resumes publicly.

## Data and AI behavior

- Resume files are parsed in memory and the extracted text/profile is stored in PostgreSQL. The original binary is not saved by the current upload endpoint.
- ChromaDB indexes text chunks for semantic retrieval. Its default embedding function may download an embedding model on first use, depending on ChromaDB version/configuration.
- The match score is calculated locally and deterministically; Gemini only produces the narrative explanation. AI-generated interview/roadmap content requires a working API key and internet access.
- Skill extraction uses a transparent list of recognizable technology terms and can miss synonyms or skills absent from the list. Review and correct source text before relying on results.
- This repository does not scrape job boards or invent current job vacancies. Users enter job descriptions or integrate a licensed job API.

## Portfolio presentation tips

1. Record a 2–3 minute demo showing resume upload → add a real JD → matching report → interview generation → saved application.
2. Include a sanitized sample resume, one sample job description, architecture diagram and test results in the repository.
3. Add measured evaluation: parsing accuracy on a consented test set, skill-extraction precision/recall, latency, and LLM cost per workflow.
4. Explain limitations and human review in your README and demo; this is a stronger engineering signal than claiming “100% accurate AI hiring.”
