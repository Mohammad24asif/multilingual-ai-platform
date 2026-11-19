"""Environment-driven settings (pydantic-settings). Variables are prefixed MLAI_; see .env.example.

STATUS: not executed in the build sandbox (pydantic-settings is not installed there). The rest of the
core is framework-free and receives a plain ``RuntimeConfig`` built by ``Settings.to_runtime()``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .runtime import RuntimeConfig


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MLAI_", env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    log_json: bool = True

    licence_mode: str = "research"  # "research" | "commercial"
    device: str = "auto"  # "auto" | "cpu" | "cuda"
    allow_model_download: bool = False
    require_safetensors: bool = False
    enabled_models: str = ""  # comma-separated model ids; empty = registry defaults
    remote_code_allowlist: str = ""  # comma-separated repo@commit entries a human has reviewed
    ram_budget_mb: int | None = Field(default=None, ge=256)
    max_loaded_models: int = Field(default=1, ge=1, le=8)
    inference_queue_size: int = Field(default=8, ge=1, le=256)
    inference_timeout_s: float = Field(default=120.0, gt=0)
    torch_threads: int | None = Field(default=None, ge=1)

    max_input_chars: int = Field(default=20_000, ge=100)
    max_segments: int = Field(default=400, ge=1)
    max_batch_size: int = Field(default=8, ge=1)
    max_batch_tokens: int = Field(default=1_600, ge=16)
    num_beams: int = Field(default=4, ge=1, le=8)
    max_request_bytes: int = Field(default=1_000_000, ge=1_000)

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    registry_dir: str | None = None
    database_url: str = "sqlite:///./data/local/app.sqlite3"

    @field_validator("licence_mode")
    @classmethod
    def _check_licence_mode(cls, value: str) -> str:
        if value not in ("research", "commercial"):
            raise ValueError("MLAI_LICENCE_MODE must be 'research' or 'commercial'")
        return value

    @field_validator("device")
    @classmethod
    def _check_device(cls, value: str) -> str:
        if value not in ("auto", "cpu", "cuda"):
            raise ValueError("MLAI_DEVICE must be 'auto', 'cpu' or 'cuda'")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return _csv(self.cors_origins)

    def to_runtime(self) -> RuntimeConfig:
        enabled = _csv(self.enabled_models)
        return RuntimeConfig(
            licence_mode=self.licence_mode,
            device=self.device,
            allow_model_download=self.allow_model_download,
            enabled_models=frozenset(enabled) if enabled else None,
            remote_code_allowlist=frozenset(_csv(self.remote_code_allowlist)),
            ram_budget_mb=self.ram_budget_mb,
            max_loaded_models=self.max_loaded_models,
            inference_queue_size=self.inference_queue_size,
            inference_timeout_s=self.inference_timeout_s,
            torch_threads=self.torch_threads,
            max_input_chars=self.max_input_chars,
            max_segments=self.max_segments,
            max_batch_size=self.max_batch_size,
            max_batch_tokens=self.max_batch_tokens,
            num_beams=self.num_beams,
            require_safetensors=self.require_safetensors,
            registry_dir=Path(self.registry_dir) if self.registry_dir else None,
        )
