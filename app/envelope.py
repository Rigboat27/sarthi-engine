from typing import Any, Optional

from app import config


def ok(data: Any = None, tokens: Optional[dict] = None, cost_inr: float = 0.0) -> dict:
    """Wrap a successful response in the canonical ApiEnvelope."""
    return {
        "ok": True,
        "data": data,
        "meta": {
            "tokens": tokens or {},
            "costEstimateInr": round(cost_inr, 6),
            "mock": config.MOCK_MODE,
        },
        "error": None,
    }


def fail(message: str, code: str = "error") -> dict:
    """Build the error form of the ApiEnvelope (pair with a JSONResponse status)."""
    return {
        "ok": False,
        "data": None,
        "meta": {"mock": config.MOCK_MODE},
        "error": {"code": code, "message": message},
    }
