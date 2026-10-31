# src/config.py
"""Application configuration using Pydantic Settings and dotenv."""

import os
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

def _load_streamlit_secrets():
    """Populate os.environ from Streamlit secrets if running in Streamlit Cloud."""
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for k, v in st.secrets.items():
                if isinstance(v, (str, int, float, bool)) and k not in os.environ:
                    os.environ[k] = str(v)
    except Exception:
        pass

_load_streamlit_secrets()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field

    class Settings(BaseSettings):
        """Application settings schema with sensible defaults."""
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

        app_env: str = Field(default="development", alias="APP_ENV")
        log_level: str = Field(default="INFO", alias="LOG_LEVEL")
        default_page_size: int = Field(default=10, alias="DEFAULT_PAGE_SIZE")

        # Database
        db_host: str = Field(default="localhost", alias="DB_HOST")
        db_port: int = Field(default=5432, alias="DB_PORT")
        db_user: str = Field(default="postgres", alias="DB_USER")
        db_password: str = Field(default="postgres", alias="DB_PASSWORD")
        db_name: str = Field(default="postgres", alias="DB_NAME")
        database_url_override: Optional[str] = Field(default=None, alias="DATABASE_URL")

        # Gemini
        gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
        gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

        @property
        def database_url(self) -> str:
            """Construct PostgreSQL SQLAlchemy database URL or use override."""
            if self.database_url_override:
                url = self.database_url_override.strip()
                if url.startswith("postgresql://"):
                    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
                url = url.replace("&channel_binding=require", "").replace("?channel_binding=require", "?")
                return url
            return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

except ImportError:
    from pydantic import BaseModel, Field, ConfigDict  # type: ignore

    class Settings(BaseModel):  # type: ignore
        model_config = ConfigDict(extra="ignore")

        app_env: str = Field(default="development", alias="APP_ENV")
        log_level: str = Field(default="INFO", alias="LOG_LEVEL")
        default_page_size: int = Field(default=10, alias="DEFAULT_PAGE_SIZE")
        db_host: str = Field(default="localhost", alias="DB_HOST")
        db_port: int = Field(default=5432, alias="DB_PORT")
        db_user: str = Field(default="postgres", alias="DB_USER")
        db_password: str = Field(default="postgres", alias="DB_PASSWORD")
        db_name: str = Field(default="postgres", alias="DB_NAME")
        database_url_override: Optional[str] = Field(default=None, alias="DATABASE_URL")
        gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
        gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

        @property
        def database_url(self) -> str:
            if self.database_url_override:
                url = self.database_url_override.strip()
                if url.startswith("postgresql://"):
                    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
                url = url.replace("&channel_binding=require", "").replace("?channel_binding=require", "?")
                return url
            return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
