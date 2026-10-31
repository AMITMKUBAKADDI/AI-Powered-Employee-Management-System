# src/ai/llm.py
"""LLM initialization and Google Gemini integration using langchain-google-genai."""

import logging
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import get_settings

logger = logging.getLogger(__name__)


def get_llm(temperature: float = 0.0) -> Optional[ChatGoogleGenerativeAI]:
    """
    Initialize and return the ChatGoogleGenerativeAI instance.
    Returns None if the API key is not configured.
    """
    settings = get_settings()
    api_key = settings.gemini_api_key

    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("GEMINI_API_KEY is not set or is using placeholder value.")
        return None

    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=api_key,
            temperature=temperature,
            convert_system_message_to_human=False
        )
        return llm
    except Exception as exc:
        logger.error("Failed to initialize Google Gemini LLM: %s", exc)
        return None
