import os


def _flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


MOCK_MODE = _flag("MOCK_MODE", "true")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SARVAM_BASE = "https://api.sarvam.ai"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Frugality guard: refuse LLM/speech spend past this many INR (crude estimate).
SPEND_CAP_INR = float(os.getenv("SPEND_CAP_INR", "100"))

# Simple in-memory spend meter (resets on restart).
_spend = {"inr": 0.0}


def add_spend(amount: float) -> float:
    _spend["inr"] += amount
    return _spend["inr"]


def spent() -> float:
    return _spend["inr"]
