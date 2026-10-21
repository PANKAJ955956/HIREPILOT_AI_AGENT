import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_hirepilot.db")
os.environ.setdefault("CHROMA_PERSIST_DIR", "./test_chroma")
