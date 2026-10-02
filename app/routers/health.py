from fastapi import APIRouter

from app import config
from app.envelope import ok

router = APIRouter()


@router.get("/health")
def health():
    return ok(
        {
            "version": "0.2.0",
            "providers": {
                "sarvam": bool(config.SARVAM_API_KEY),
                "gemini": bool(config.GEMINI_API_KEY),
                "aa": "mock",
            },
            "mockMode": config.MOCK_MODE,
            "spendInr": round(config.spent(), 4),
            "capINR": config.SPEND_CAP_INR,
        }
    )
