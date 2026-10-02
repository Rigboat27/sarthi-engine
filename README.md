# sarthi-engine

The **Sarthi Core** backend — a single FastAPI service (Python 3.12) that every
client (Chrome extension, Viraasat portal) talks to. It holds the API keys so they
never reach the browser, and exposes speech, LLM, docs, AA, and shared data.

## Run it

```bash
# create a virtualenv (recommended)
python -m venv .venv
.venv\Scripts\activate        # Windows

pip install -r requirements.txt
copy .env.example .env        # fill in keys only when going live
python run.py                 # http://127.0.0.1:8787
```

Defaults are **mock-first** (`MOCK_MODE=true`): `/speech/*`, `/llm/*` and `/aa/*`
return canned data with zero network calls and zero spend.

## Endpoints

| Route | Description |
|---|---|
| `GET /health` | liveness + which providers are live + spend meter |
| `POST /speech/stt` | audio → transcript (Sarvam Saaras v4; mock in MOCK_MODE) |
| `POST /speech/tts` | text → audio b64 (Sarvam Bulbul v3; cached mock) |
| `POST /llm/chat` | conversation (Gemini; mock in MOCK_MODE) |
| `POST /docs/ocr` | document → text/fields (Team B, mock here) |
| `POST /docs/match` | fuzzy name match (rapidfuzz) |
| `POST /docs/affidavit` | affidavit payload → doc (Team B, mock here) |
| `GET /aa/aggregators` | list AA providers |
| `POST /aa/consent` | create consent artefact |
| `POST /aa/verify` | verify consent (OTP) |
| `POST /aa/fetch` | fetch FIP holdings |
| `GET /data/rules` | canonical SEBI timelines |
| `GET /data/brokers` | broker grievance directory |

Every response uses the canonical envelope from `sarthi-contracts`:
`{ ok, data, meta:{tokens, costEstimateInr, mock}, error }`.

## Keys (going live)

`MOCK_MODE=false`, then set in `.env`:
- `SARVAM_API_KEY` — https://dashboard.sarvam.ai
- `GEMINI_API_KEY` — https://aistudio.google.com/apikey

Sarvam auth uses the `api-subscription-key` header; a `403` means an auth failure.

## Note on `/data/*`

`app/data/scoresRules.json` and `app/data/brokerDirectory.json` are the canonical
copies. Values are seeded but marked `verified:false` — Team A should merge in their
already-verified values so extension and portal share one source.
