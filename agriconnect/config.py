"""Configuration and lightweight .env loader (no external dependency)."""
from __future__ import annotations
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = str(DATA_DIR / "agri.db")


def _load_dotenv() -> None:
    """Minimal .env parser so we don't depend on python-dotenv.

    Reads KEY=VALUE lines from a .env file at the project root and sets them
    in os.environ only if not already present.
    """
    env_path = BASE_DIR.parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

# --- LLM provider (auto-detected) ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
CHAT_MODEL = os.environ.get("AGRI_CHAT_MODEL", "gpt-4o-mini")
PROVIDER = "openai" if OPENAI_API_KEY else "local"

# --- Retrieval / agent behaviour ---
RETRIEVAL_TOP_K = int(os.environ.get("AGRI_TOP_K", "3"))
# Minimum cosine similarity for a retrieved chunk to count as "supporting
# evidence". Below this the assistant abstains and hands off to staff.
ABSTAIN_THRESHOLD = float(os.environ.get("AGRI_ABSTAIN_THRESHOLD", "0.06"))
# A single shared term is only trusted when the similarity is at least this high.
STRONG_SINGLE_TERM_SCORE = float(os.environ.get("AGRI_STRONG_SINGLE", "0.12"))
MAX_AGENT_STEPS = int(os.environ.get("AGRI_MAX_STEPS", "3"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
