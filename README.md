# sarthi-engine

FastAPI backend for the Sarthi stack. One service on 127.0.0.1:8787 serves the portal, the Chrome extension, and the contract tests. It holds the Gemini and Sarvam keys so no key ever ships in frontend code.

```
                    +-----------------------------+
                    | sarthi-engine :8787         |
                    | main.py + CORS              |
                    +------+------+------+-------+
                           |      |      |
              +------------+ +----+ +----+------------+
              | proxy.py     | aa.py | docs.py          |
              | /stt /tts   | consent| /docs/ocr       |
              | /llm/chat   | verify | /docs/match     |
              | /gemini/*   | fetch  | /docs/affidavit |
              | /sarvam/*   |        | /docs/vault-pdf |
              +------------+ +----+ +----+------------+
                           |      |      |
                    +------+------+------+------+
                    | health.py  data.py        |
                    | /health    /data/rules    |
                    |            /data/brokers  |
                    |            /data/nodal    |
                    +--------------------------+
                           |
              +------------+------------+
              | services/  models/  aa/ |
              | gemini.py  holding  mock|
              | docs.py    grievance_data|
              |            affidavit    |
              +-------------------------+
```

## Responsibilities

- Proxy Sarvam speech and Gemini chat and vision with the keys from `.env`.
- Serve the Account Aggregator mock with Setu and Finvu shaped consent and FIP records.
- Run the docs pipeline with OCR, fuzzy match, affidavit generation, and PDF rendering.
- Serve canonical shared data for SEBI rules, broker grievance emails, and company routing.
- Report liveness and provider flags on `/health`.

## Routers

- `app/routers/proxy.py` serves extension compatible routes. `/stt` and `/speech/stt` accept multipart audio and return text with `detectedLang`. `/tts` and `/speech/tts` accept text with language code and return base64 audio arrays. `/llm/chat` accepts a Gemini body with `model` inside and walks a fallback chain. `/gemini/{model}:generateContent` and `/sarvam/v1/chat/completions` pass vendor bodies through untouched. Shapes stay raw because the extension already parses them.
- `app/routers/aa.py` implements the mock AA flow. `/aa/aggregators` lists OneMoney, CAMS Finserv, Finvu, and Setu. `/aa/consent` creates a consent id plus a Sahamati style artefact. `/aa/verify` marks consent verified. `/aa/fetch` returns `ownerName` and grouped FIP records and rejects unverified consent with 403.
- `app/routers/docs.py` implements `/docs/ocr` with KYC plus certificate uploads, `/docs/match` with rapidfuzz scoring, `/docs/affidavit` for transmission, `/docs/name-affidavit` for IEPF name mismatch, and `/docs/vault-pdf` for the family vault summary.
- `app/routers/data.py` serves `/data/rules` with verified SEBI timelines and source URLs, `/data/brokers` with name search across `names` arrays and verified flags, and `/data/nodal` with 119 listed companies plus public RTA investor emails.
- `app/routers/health.py` returns version, provider flags for Sarvam and Gemini and AA, mock mode, spend meter, and cap.

## Services

- `app/services/gemini.py` wraps `generateContent` with `generate_with_fallback` across `gemini-3.5-flash-lite`, `gemini-flash-lite-latest`, and `gemini-3-flash-preview`. It also parses candidate text and builds `inlineData` image parts from data URLs.
- `app/services/docs.py` holds the domain logic. OCR compares KYC and certificate names through Gemini Vision. Name affidavit generation runs through Gemini. Transmission affidavit uses a deterministic template of the official SEBI format, so no model can invent a clause. PDF rendering uses reportlab with Times plus Noto Sans Devanagari for Hindi names. Vault PDF renders owner, account table, and nominee flags.

## Models

- `app/models/holding.py` defines `AccountType`, `Nominee`, and `Holding` in lockstep with `holding.schema.json`.
- `app/models/grievance.py` defines `GrievanceState` with combined `clientIdFolioNoDpid`, `PriorContactProof` enum, object `attachments`, and fields such as `priorContactConfirmed` and `skippedFields`.
- `app/models/affidavit.py` defines `Affidavit` with deceased, applicant, gender, father name, shareholding, death details, family tree, and NOC list.

## Data files

- `app/data/scoresRules.json` stores verified SEBI timelines with source URL and check date.
- `app/data/brokerDirectory.json` stores 18 brokers. Ten grievance emails are marked verified after checking policy pages, including Zerodha, Groww, Upstox, Angel One, ICICI Direct, HDFC Securities, Kotak, Sharekhan, Motilal Oswal, and 5paisa.
- `app/data/nodalOfficers.json` stores 119 listed companies with name, ticker, sector, and RTA. Mailing addresses are intentionally absent. The API attaches the RTA public investor email and a warning to confirm the company Nodal Officer page before posting.
- `app/aa/mock_data.py` seeds nine holdings across HDFC, SBI, ICICI, CDSL, NSDL, CAMS, KFintech, LIC, and PPF. Five carry verified nominees and four carry none, which drives the demo health score.
- `app/fonts/` bundles Noto Sans Devanagari regular and bold for PDF names.

## Config and envelope

`app/config.py` loads the root `.env` into process env, then exposes `MOCK_MODE`, `SARVAM_API_KEY`, `GEMINI_API_KEY`, `GEMINI_MODELS`, spend rates, and an in memory spend meter. `app/envelope.py` builds the canonical `ok`, `data`, `meta`, and `error` wrapper for all `/aa/*`, `/docs/*`, `/data/*`, and `/health` responses.

## Environment

Copy `.env.example` to `.env`.

```bash
MOCK_MODE=false
GEMINI_API_KEY=AIza...
SARVAM_API_KEY=...
SPEND_CAP_INR=100
```

Mock mode returns canned data with zero spend. Live mode calls Sarvam at `api.sarvam.ai` and Gemini at `generativelanguage.googleapis.com`. A 403 from Sarvam means bad auth.

## Run and test

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Then in another shell:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -q
.\.venv\Scripts\python.exe smoke.py
```

`tests/test_contracts.py` validates engine output against `sarthi-contracts` schemas with `jsonschema`. `smoke.py` hits health, AA consent through fetch, match, affidavit, OCR, data routes, and proxy routes, and tolerates live mode skips when a vendor key is absent.
