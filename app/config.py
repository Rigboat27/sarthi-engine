import os


def _load_dotenv() -> None:
    """Load the engine root .env into os.environ (only if the var isn't already set)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def _flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


MOCK_MODE = _flag("MOCK_MODE", "true")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SARVAM_BASE = "https://api.sarvam.ai"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Gemini model fallback chain (verified Oct 2026 — "gemini-2.5-flash" now 404s).
GEMINI_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_MODELS",
        "gemini-3.5-flash-lite,gemini-flash-lite-latest,gemini-3-flash-preview",
    ).split(",")
    if m.strip()
]

# Frugality guard: refuse LLM/speech spend past this many INR (crude estimate).
SPEND_CAP_INR = float(os.getenv("SPEND_CAP_INR", "100"))

# Spend rates (INR), observed Sarvam pricing — used only for estimates.
STT_RATE_PER_HOUR = 30.0
TTS_RATE_PER_10K_CHARS = 30.0
SARVAM_LLM_IN_PER_1M = 29.28
SARVAM_LLM_OUT_PER_1M = 73.2

# Simple in-memory spend meter (resets on restart).
_spend = {"inr": 0.0}


def add_spend(amount: float) -> float:
    _spend["inr"] += amount
    return _spend["inr"]


def spent() -> float:
    return _spend["inr"]
