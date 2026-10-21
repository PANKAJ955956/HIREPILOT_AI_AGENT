from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings

def get_llm(temperature: float = 0.2):
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured. Add it to your .env file.")
    return ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key, temperature=temperature)
