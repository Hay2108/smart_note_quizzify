from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_url: str = f"sqlite:///{(ROOT / 'smart_note.db').as_posix()}"
    ai_provider: str = "gemini"
    gemini_api_key: str = field(default="", repr=False)
    openai_api_key: str = field(default="", repr=False)
    gemini_model: str = ""
    openai_model: str = ""
    ai_timeout_seconds: float = 120
    ai_max_retries: int = 1
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 20
    cors_origins: tuple[str, ...] = ("http://localhost:8501", "http://127.0.0.1:8501")

    def __post_init__(self):
        if self.ai_provider not in {"gemini", "openai"}:
            raise ValueError("AI_PROVIDER must be gemini or openai")
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("This project requires a SQLite database URL")
        if not (0 < self.max_upload_bytes <= 10 * 1024 * 1024):
            raise ValueError("MAX_UPLOAD_MB must be between 1 and 10")
        if not (1 <= self.max_pdf_pages <= 100):
            raise ValueError("MAX_PDF_PAGES must be between 1 and 100")
        if not (0 < self.ai_timeout_seconds <= 600):
            raise ValueError("AI_TIMEOUT_SECONDS must be between 0 and 600")
        if not (0 <= self.ai_max_retries <= 3):
            raise ValueError("AI_MAX_RETRIES must be between 0 and 3")

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env", override=True)
        return cls(
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            ai_provider=os.getenv("AI_PROVIDER", "gemini").strip().lower(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1").strip(),
            ai_timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "120")),
            ai_max_retries=int(os.getenv("AI_MAX_RETRIES", "1")),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
            max_pdf_pages=int(os.getenv("MAX_PDF_PAGES", "20")),
            cors_origins=tuple(x.strip() for x in os.getenv(
                "CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501"
            ).split(",") if x.strip()),
        )
