"""Central settings. Every threshold the routing rules depend on lives here,
so changing business policy never requires touching pipeline code."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    # LLM (Ollama)
    ollama_host: str = "http://localhost:11434"
    triage_model: str = "qwen2.5:3b"
    agent_model: str = "qwen2.5:7b"
    judge_model: str = "qwen2.5:7b"
    llm_temperature: float = 0.0
    llm_num_ctx: int = 8192
    llm_timeout_s: float = 300.0
    embedding_model: str = "bge-m3"  # multilingual (Arabic); "default" = Chroma's English-only MiniLM

    # Routing / HITL
    refund_escalation_threshold: float = 200.0
    auto_send_confidence: float = 0.85
    very_negative_sentiment: float = -0.7
    low_risk_categories: tuple[str, ...] = ("shipping", "technical", "account", "other")

    # "Today" for the mock world. Fixed so refund-window checks are reproducible
    # (an order delivered 29 days ago must stay 29 days old when you rerun evals).
    reference_date: str = "2026-11-01"

    # Auth
    jwt_secret: str = "dev-insecure-change-me"  # MUST be overridden outside local dev
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    environment: str = "dev"  # dev | prod (prod refuses to start with the default secret)
    trusted_proxies: str = "127.0.0.1,::1"  # peers allowed to set X-Forwarded-For (the Next.js server)
    # Failed-login limits per 15-minute window
    login_window_minutes: int = 15
    login_max_per_account_ip: int = 5
    login_max_per_account: int = 10
    login_max_per_ip: int = 30

    # Worker
    worker_poll_seconds: float = 1.0
    job_lock_timeout_s: int = 900  # a "running" job older than this is presumed dead and requeued

    # Storage
    database_url: str = f"sqlite:///{ROOT_DIR / 'storage' / 'app.db'}"
    chroma_dir: str = str(ROOT_DIR / "storage" / "chroma")


@lru_cache
def get_settings() -> Settings:
    return Settings()
