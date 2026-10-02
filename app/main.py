from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import aa, data, docs, health, proxy

app = FastAPI(
    title="Sarthi Core",
    version="0.1.0",
    description="Single backend for the Sarthi SEBI Track B stack (speech, LLM, docs, AA, data).",
)

# Dev CORS: portal (localhost:3000) and the MV3 extension both talk to this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(proxy.router)
app.include_router(docs.router)
app.include_router(aa.router)
app.include_router(data.router)
