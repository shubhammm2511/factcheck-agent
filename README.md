# Fact-Check Agent

> AI-powered PDF claim verification. Upload a document, get a verdict on every factual claim.

**Stack:** Python · Streamlit · Grok (xAI) · Tavily · PyMuPDF

---

## What It Does

1. **Upload** a PDF (marketing report, press release, research paper)
2. **Extracts** verifiable claims — percentages, financial figures, market sizes, growth claims, dates
3. **Searches** the live web via Tavily for evidence per claim
4. **Verifies** each claim with Grok, returning a structured JSON verdict
5. **Reports** each claim as `Verified`, `Inaccurate`, `False`, or `Unverifiable` with corrected facts and sources

---

## Project Structure

```
factcheck-agent/
├── app.py                      # Streamlit UI + pipeline orchestration
├── config.py                   # All config, env vars, constants
├── requirements.txt
├── .env.example
│
├── services/
│   ├── pdf_service.py          # PyMuPDF text extraction
│   ├── claim_service.py        # Regex + NLP claim extraction
│   ├── search_service.py       # Tavily web search
│   └── verification_service.py # Grok API + verdict parsing
│
├── prompts/
│   └── verifier_prompt.py      # Grok system + user prompts
│
├── models/
│   └── schemas.py              # Dataclasses: Claim, SearchResult, Verdict
│
└── utils/
    ├── logger.py               # Centralized logging
    └── text_helpers.py         # Text cleaning, sentence splitting
```

---

## Local Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/factcheck-agent.git
cd factcheck-agent
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and add your keys:
# GROK_API_KEY=xai-...
# TAVILY_API_KEY=tvly-...
```

Get your keys:
- **Grok:** https://console.x.ai → API Keys
- **Tavily:** https://app.tavily.com → Dashboard

### 3. Run

```bash
streamlit run app.py
```

Open http://localhost:8501

---

## Deploy to Streamlit Cloud

1. Push your repo to GitHub (make sure `.env` is in `.gitignore`)
2. Go to https://share.streamlit.io → New app
3. Select your repo + `app.py` as the entry point
4. Under **Advanced settings → Secrets**, add:

```toml
GROK_API_KEY = "xai-your-key-here"
TAVILY_API_KEY = "tvly-your-key-here"
```

5. Click **Deploy** — your app will be live at `https://your-app.streamlit.app`

> Streamlit secrets are automatically loaded as environment variables, so `config.py` picks them up with no changes.

---

## Evaluation Notes

When tested with a "trap document" (intentional fake stats), the system:

- Detects outdated statistics (e.g., "2019 market size" when 2024 data differs)
- Flags hallucinated figures (no corroborating evidence found)
- Catches wrong numbers even when the topic is correct (e.g., correct company, wrong revenue)
- Provides corrected facts with source URLs

**Tuning tips:**
- Increase `TAVILY_MAX_RESULTS` in `config.py` for more evidence per claim
- Switch `GROK_MODEL` to `grok-3` (vs `grok-3-mini`) for higher accuracy on complex claims
- Adjust `MAX_CLAIMS_PER_DOC` to control API cost vs. thoroughness

---

## Architecture Decisions

| Decision | Rationale |
|---|---|
| No LangChain | Avoids abstraction overhead; direct API calls are faster to debug |
| Regex claim extraction | No NLTK/spaCy dependency; fast; works well for numeric claims |
| Dataclasses for schemas | Type safety without Pydantic overhead |
| OpenAI SDK for Grok | xAI's API is OpenAI-compatible; one less dependency |
| Tavily `advanced` depth | Better snippet quality than `basic`; worth the extra latency |