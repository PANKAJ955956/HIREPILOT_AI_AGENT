.PHONY: install api dashboard test
install:
	python -m pip install -r backend/requirements.txt -r frontend/requirements.txt pytest
api:
	cd backend && uvicorn app.main:app --reload --port 8000
dashboard:
	cd frontend && streamlit run app.py --server.port 8501
test:
	pytest -q
