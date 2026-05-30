from functools import lru_cache

from pydantic import Field, field_validator
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
    host_data_sources_path: str = Field(
        default="",
        description=(
            "Optional host path for sources (e.g. I:/VECTORDB-BRAIN/data/sources); "
            "mapped to data_sources_path in API."
        ),
    )

    logs_dir: str = "logs"
    ui_logging_enabled: bool = True
    request_logging_enabled: bool = True

    curation_gate_enabled: bool = True
    curation_gate_roots: list[str] = Field(default_factory=lambda: ["curated"])
    curation_allow_override: bool = False

    @field_validator("curation_gate_roots", mode="before")
    @classmethod
    def _parse_gate_roots(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value  # type: ignore[return-value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
