from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "omnikb-api"
    app_env: str = "dev"
    app_port: int = 8000

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "omnikb_documents"
    qdrant_timeout_seconds: float = 15.0

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_strategy: str = "recursive_char_v1"
    chunk_size: int = Field(default=450, ge=64, le=2048)
    chunk_overlap: int = Field(default=60, ge=0, le=1024)
    pipeline_version: str = "0.1.0"
    normalization_profile: str = "utf8_ignore_pypdf_v1"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    data_sources_path: str = "/data/sources"


@lru_cache
def get_settings() -> Settings:
    return Settings()
