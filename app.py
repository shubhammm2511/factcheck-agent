"""
app.py - Fact-Check Agent
Supports: plain text input + PDF upload
Theme: Black / Deep Purple
"""

import sys
import os
import html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import config
from services.pdf_service import extract_text_from_pdf, get_pdf_metadata, PDFExtractionError
from services.claim_service import extract_claims, get_claim_type_label
from services.search_service import search_claim
from services.verification_service import verify_claim
from models.schemas import VerdictStatus
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="Fact-Check Agent",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    background: #07070e !important;
    color: #e2dcff !important;
    font-family: 'JetBrains Mono', monospace !important;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
.block-container {
    padding: 0 3rem 5rem !important;
    max-width: 1080px !important;
    margin: 0 auto !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #07070e; }
::-webkit-scrollbar-thumb { background: #2e1f6e; border-radius: 4px; }

/* ════════════════════════════
   HERO
════════════════════════════ */
.hero {
    text-align: center;
    padding: 4.5rem 0 3rem;
    position: relative;
}
.hero-glow {
    position: absolute;
    top: 0; left: 50%;
    transform: translateX(-50%);
    width: 700px; height: 350px;
    background: radial-gradient(ellipse at center, rgba(109,40,217,0.18) 0%, transparent 65%);
    pointer-events: none;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.62rem;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: #a78bfa;
    background: rgba(124,58,237,0.1);
    border: 1px solid rgba(124,58,237,0.25);
    border-radius: 100px;
    padding: 0.4rem 1.1rem;
    margin-bottom: 1.8rem;
}
.hero-badge-dot {
    width: 5px; height: 5px;
    background: #7c3aed;
    border-radius: 50%;
    box-shadow: 0 0 8px #7c3aed;
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.7); }
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(3.2rem, 7vw, 5.8rem);
    font-weight: 800;
    line-height: 0.95;
    letter-spacing: -0.04em;
    background: linear-gradient(140deg, #ffffff 0%, #c4b5fd 45%, #7c3aed 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 1.2rem;
}
.hero-sub {
    font-size: 0.78rem;
    color: #3d3460;
    letter-spacing: 0.08em;
    line-height: 2;
}
.hero-line {
    width: 1px;
    height: 40px;
    background: linear-gradient(180deg, transparent, #7c3aed, transparent);
    margin: 2rem auto 0;
}

/* ════════════════════════════
   INPUT PANEL
════════════════════════════ */
.input-panel {
    background: linear-gradient(160deg, #0d0a1e 0%, #100c21 100%);
    border: 1px solid #1c1540;
    border-radius: 20px;
    padding: 2rem 2.2rem 2.4rem;
    position: relative;
    overflow: hidden;
    margin-bottom: 1rem;
}
.input-panel::before {
    content: '';
    position: absolute;
    top: 0; left: 10%; right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, #7c3aed, transparent);
    opacity: 0.7;
}
.section-label {
    font-size: 0.6rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: #4a3a80;
    margin-bottom: 0.9rem;
    font-family: 'JetBrains Mono', monospace;
}

.brief-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: #1c1540;
    border: 1px solid #1c1540;
    border-radius: 16px;
    overflow: hidden;
    margin: 0 0 1.2rem;
}
.brief-item {
    background: #0d0a1e;
    padding: 1rem;
}
.brief-kicker {
    font-family: 'Syne', sans-serif;
    font-size: 0.78rem;
    font-weight: 800;
    color: #a78bfa;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}
.brief-copy {
    font-size: 0.68rem;
    color: #5a4a8a;
    line-height: 1.65;
}

/* ── Text area ── */
.stTextArea > div > div > textarea {
    background: #09071a !important;
    border: 1px solid #1e1545 !important;
    border-radius: 12px !important;
    color: #c4b5fd !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.83rem !important;
    line-height: 1.75 !important;
    padding: 1rem 1.2rem !important;
    caret-color: #7c3aed !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    resize: vertical !important;
    min-height: 140px !important;
}
.stTextArea > div > div > textarea:focus {
    border-color: #6d28d9 !important;
    box-shadow: 0 0 0 3px rgba(109,40,217,0.12) !important;
    outline: none !important;
}
.stTextArea > div > div > textarea::placeholder {
    color: #241d42 !important;
}
.stTextArea label {
    display: none !important;
}

/* ── Divider ── */
.or-divider {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 1.4rem 0;
    color: #1e1840;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
}
.or-divider::before, .or-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, transparent, #1e1840);
}
.or-divider::after {
    background: linear-gradient(90deg, #1e1840, transparent);
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: transparent !important;
}
[data-testid="stFileUploader"] > div {
    background: #09071a !important;
    border: 1px dashed #1e1545 !important;
    border-radius: 12px !important;
    transition: all 0.25s !important;
    padding: 1.2rem !important;
}
[data-testid="stFileUploader"] > div:hover {
    border-color: #6d28d9 !important;
    background: #0c0920 !important;
}
[data-testid="stFileUploader"] label {
    color: #3d3460 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stFileUploader"] button {
    background: rgba(109,40,217,0.15) !important;
    border: 1px solid #4c1d95 !important;
    color: #a78bfa !important;
    border-radius: 7px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
}

/* ── Stat chips ── */
.chip-row {
    display: flex; gap: 0.6rem; flex-wrap: wrap; margin: 1rem 0 0;
}
.chip {
    background: rgba(124,58,237,0.07);
    border: 1px solid #2a1f50;
    border-radius: 6px;
    padding: 0.3rem 0.8rem;
    font-size: 0.7rem;
    color: #5a4a8a;
    font-family: 'JetBrains Mono', monospace;
}
.chip b { color: #9d7dff; font-weight: 500; }

/* ── Submit button ── */
.stButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 50%, #7c3aed 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #ede9fe !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    padding: 0.85rem 2rem !important;
    cursor: pointer !important;
    transition: all 0.25s !important;
    box-shadow: 0 4px 24px rgba(109,40,217,0.35) !important;
    text-transform: uppercase !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 50%, #8b5cf6 100%) !important;
    box-shadow: 0 6px 32px rgba(109,40,217,0.55) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ── Progress ── */
.progress-wrap {
    background: #0d0a1e;
    border: 1px solid #1c1540;
    border-radius: 14px;
    padding: 1.5rem 2rem;
    margin: 1rem 0;
}
.progress-title {
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #5a4a8a;
    margin-bottom: 0.8rem;
}
.stProgress > div {
    background: #0f0c22 !important;
    border-radius: 6px !important;
    height: 6px !important;
}
.stProgress > div > div {
    background: linear-gradient(90deg, #4c1d95, #7c3aed, #a78bfa) !important;
    border-radius: 6px !important;
}
.progress-status {
    font-size: 0.7rem;
    color: #3d3460;
    margin-top: 0.6rem;
    font-family: 'JetBrains Mono', monospace;
    min-height: 1.2rem;
}

/* ════════════════════════════
   RESULTS
════════════════════════════ */
.results-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: #e2dcff;
    letter-spacing: -0.03em;
    margin-bottom: 0.3rem;
}
.results-meta {
    font-size: 0.7rem;
    color: #2e2854;
    letter-spacing: 0.1em;
    margin-bottom: 2rem;
}

/* ── Summary tiles ── */
.tiles {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #1c1540;
    border: 1px solid #1c1540;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 2rem;
}
.tile {
    background: #0d0a1e;
    padding: 1.4rem 1rem;
    text-align: center;
}
.tile-num {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 0.4rem;
}
.tile-label {
    font-size: 0.62rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #2e2854;
    font-family: 'JetBrains Mono', monospace;
}
.n-total { color: #7c3aed; }
.n-verified { color: #10b981; }
.n-inaccurate { color: #f59e0b; }
.n-false { color: #ef4444; }

/* ── Filter radio ── */
.stRadio > div {
    gap: 0.5rem !important;
    flex-wrap: wrap !important;
}
.stRadio label {
    background: #0d0a1e !important;
    border: 1px solid #1c1540 !important;
    border-radius: 8px !important;
    padding: 0.35rem 1rem !important;
    font-size: 0.72rem !important;
    color: #4a3a80 !important;
    font-family: 'JetBrains Mono', monospace !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
}
.stRadio label:hover {
    border-color: #4c1d95 !important;
    color: #a78bfa !important;
}
[data-testid="stRadio"] [aria-checked="true"] + div label {
    background: rgba(124,58,237,0.15) !important;
    border-color: #6d28d9 !important;
    color: #c4b5fd !important;
}

/* ── Verdict cards ── */
.vcard {
    background: #0d0a1e;
    border: 1px solid #1c1540;
    border-radius: 16px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 0.9rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.vcard:hover { border-color: #2e1f6e; box-shadow: 0 4px 24px rgba(109,40,217,0.08); }
.vcard::before {
    content: '';
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 3px;
}
.vcard-verified::before   { background: #10b981; }
.vcard-inaccurate::before { background: #f59e0b; }
.vcard-false::before      { background: #ef4444; }
.vcard-unverifiable::before { background: #4b5563; }

.vcard-type {
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #2e2854;
    margin-bottom: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
}
.vcard-claim {
    font-size: 0.88rem;
    color: #9d8ecf;
    line-height: 1.7;
    font-style: italic;
    margin-bottom: 1.1rem;
    font-family: 'JetBrains Mono', monospace;
}
.vcard-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 0.9rem;
}
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.28rem 0.85rem;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'Syne', sans-serif;
    letter-spacing: 0.05em;
}
.badge-verified    { background: rgba(16,185,129,0.1);  color: #10b981; border: 1px solid rgba(16,185,129,0.25); }
.badge-inaccurate  { background: rgba(245,158,11,0.1);  color: #f59e0b; border: 1px solid rgba(245,158,11,0.25); }
.badge-false       { background: rgba(239,68,68,0.1);   color: #ef4444; border: 1px solid rgba(239,68,68,0.25); }
.badge-unverifiable{ background: rgba(75,85,99,0.15);   color: #6b7280; border: 1px solid rgba(75,85,99,0.3); }

.conf {
    font-size: 0.68rem;
    color: #2e2854;
    font-family: 'JetBrains Mono', monospace;
}
.conf b { color: #5a4a8a; }

.reasoning {
    background: #09071a;
    border-left: 2px solid #1c1540;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1rem;
    font-size: 0.78rem;
    color: #4a3a80;
    line-height: 1.8;
    margin-bottom: 0.9rem;
    font-family: 'JetBrains Mono', monospace;
}

.correction-label {
    font-size: 0.58rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #065f46;
    margin-bottom: 0.3rem;
    font-family: 'JetBrains Mono', monospace;
}
.correction {
    background: rgba(16,185,129,0.05);
    border: 1px solid rgba(16,185,129,0.15);
    border-radius: 8px;
    padding: 0.7rem 1rem;
    font-size: 0.78rem;
    color: #34d399;
    line-height: 1.7;
    margin-bottom: 0.9rem;
    font-family: 'JetBrains Mono', monospace;
}

.src-link {
    display: inline-block;
    font-size: 0.67rem;
    color: #6d28d9;
    text-decoration: none;
    background: rgba(109,40,217,0.08);
    border: 1px solid rgba(109,40,217,0.2);
    border-radius: 5px;
    padding: 0.18rem 0.55rem;
    margin: 0.15rem 0.2rem 0.15rem 0;
    font-family: 'JetBrains Mono', monospace;
    word-break: break-all;
    transition: all 0.15s;
}
.src-link:hover { background: rgba(109,40,217,0.18); color: #a78bfa; }

/* ── Score ── */
.score-wrap {
    text-align: center;
    padding: 3rem 0 1rem;
}
.score-label {
    font-size: 0.6rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: #2e2854;
    margin-bottom: 0.8rem;
    font-family: 'JetBrains Mono', monospace;
}
.score-num {
    font-family: 'Syne', sans-serif;
    font-size: 5rem;
    font-weight: 800;
    line-height: 1;
}
.score-unit { font-size: 2.5rem; color: #2e2854; }
.score-desc {
    font-size: 0.72rem;
    color: #2e2854;
    margin-top: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Alerts ── */
.stAlert {
    background: #0d0a1e !important;
    border: 1px solid #1c1540 !important;
    border-radius: 10px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    color: #a78bfa !important;
}

/* ── HR ── */
hr { border-color: #1c1540 !important; margin: 2rem 0 !important; }

/* ── Status widget ── */
[data-testid="stStatusWidget"] {
    background: #0d0a1e !important;
    border: 1px solid #1c1540 !important;
    border-radius: 12px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    color: #a78bfa !important;
}

@media (max-width: 760px) {
    .block-container { padding: 0 1rem 4rem !important; }
    .hero { padding: 3.5rem 0 2.2rem; }
    .hero-title { font-size: clamp(2.6rem, 15vw, 4rem); }
    .brief-grid { grid-template-columns: 1fr; }
    .tiles { grid-template-columns: repeat(2, 1fr); }
    .input-panel { padding: 1.4rem 1.2rem 1.7rem; border-radius: 16px; }
}

@media (max-width: 480px) {
    .tiles { grid-template-columns: 1fr; }
}

/* ── Footer ── */
.footer {
    text-align: center;
    padding: 2.5rem 0 0;
    font-size: 0.6rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #1c1540;
    font-family: 'JetBrains Mono', monospace;
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════
# HERO
# ════════════════════════════════════════════

st.markdown("""
<div class="hero">
    <div class="hero-glow"></div>
    <div class="hero-badge">
        <div class="hero-badge-dot"></div>
        Live PDF Verification
    </div>
    <div class="hero-title">Fact-Check<br>Agent</div>
    <div class="hero-sub">Upload a PDF &nbsp;·&nbsp; Extract stats, dates, financial and technical claims &nbsp;·&nbsp; Verify against live web evidence</div>
    <div class="hero-line"></div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════
# CONFIG CHECK
# ════════════════════════════════════════════

errors = config.validate_config()
if errors:
    for err in errors:
        st.error(f"⚙️ {err}")
    st.info("Add your API keys to a `.env` file.")
    st.stop()


# ════════════════════════════════════════════
# INPUT PANEL
# ════════════════════════════════════════════

st.markdown('<div class="input-panel">', unsafe_allow_html=True)
st.markdown("""
<div class="brief-grid">
    <div class="brief-item">
        <div class="brief-kicker">Extract</div>
        <div class="brief-copy">Find specific claims with statistics, dates, financial figures, market data, and technical specs.</div>
    </div>
    <div class="brief-item">
        <div class="brief-kicker">Verify</div>
        <div class="brief-copy">Search the live web for evidence and compare each claim against current reliable sources.</div>
    </div>
    <div class="brief-item">
        <div class="brief-kicker">Report</div>
        <div class="brief-copy">Flag every claim as Verified, Inaccurate, or False and show corrected facts when the document is wrong.</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-label">Upload the PDF to evaluate</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    label="Upload PDF",
    type=["pdf"],
    label_visibility="collapsed",
)

# Show file metadata if PDF uploaded
if uploaded_file:
    pdf_bytes_preview = uploaded_file.read()
    uploaded_file.seek(0)
    meta = get_pdf_metadata(pdf_bytes_preview)
    file_name = html.escape(uploaded_file.name)
    author = html.escape(meta.get("author", "Unknown"))
    author_chip = f"<div class='chip'>By <b>{author}</b></div>" if author not in ("Unknown", "") else ""
    st.markdown(f"""
    <div class="chip-row">
        <div class="chip">PDF <b>{file_name}</b></div>
        <div class="chip">Pages <b>{meta['page_count']}</b></div>
        <div class="chip">Size <b>{meta['file_size_mb']} MB</b></div>
        {author_chip}
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # close input-panel

# Submit button
has_input = uploaded_file is not None
run_btn = st.button("Run PDF Fact-Check", disabled=not has_input)


# ════════════════════════════════════════════
# PIPELINE
# ════════════════════════════════════════════

if run_btn and has_input:
    results = []
    raw_text = ""

    try:
        with st.status("Preparing PDF for verification...", expanded=True) as status:
            st.write("Extracting text from PDF...")
            pdf_bytes = uploaded_file.read()
            raw_text, page_count = extract_text_from_pdf(pdf_bytes)
            st.write(f"Extracted {len(raw_text):,} characters from {page_count} pages")

            # Claim extraction
            st.write("Identifying specific claims: statistics, dates, financial figures, and technical specs...")
            claims = extract_claims(raw_text)

            if not claims:
                st.warning("No specific verifiable claims found. Upload a PDF with statistics, dates, financial figures, market data, or technical specs.")
                st.stop()

            st.write(f"Found **{len(claims)}** verifiable claims")
            status.update(label=f"Extracted {len(claims)} claims", state="complete")

        # Progress bar
        st.markdown('<div class="progress-wrap">', unsafe_allow_html=True)
        st.markdown('<div class="progress-title">Verifying claims against live web data</div>', unsafe_allow_html=True)
        progress_bar = st.progress(0)
        status_text = st.empty()
        st.markdown('</div>', unsafe_allow_html=True)

        for i, claim in enumerate(claims):
            progress_bar.progress(i / len(claims))
            claim_preview = html.escape(claim.text[:90])
            ellipsis = "..." if len(claim.text) > 90 else ""
            status_text.markdown(
                f'<div class="progress-status">[{i+1}/{len(claims)}] {claim_preview}{ellipsis}</div>',
                unsafe_allow_html=True,
            )
            search_results = search_claim(claim)
            result = verify_claim(claim, search_results)
            if result.verdict.status == VerdictStatus.UNVERIFIABLE:
                result.verdict.status = VerdictStatus.FALSE
                result.verdict.reasoning = (
                    "No credible live web evidence was found that supports this claim. "
                    f"Original verifier note: {result.verdict.reasoning}"
                )
            results.append(result)

        progress_bar.progress(1.0)
        status_text.markdown(
            '<div class="progress-status" style="color:#10b981;">All claims verified and reported</div>',
            unsafe_allow_html=True,
        )

    except PDFExtractionError as e:
        st.error(f"PDF Error: {e}")
        st.stop()
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        st.error(f"Unexpected error: {e}")
        st.stop()

    # ════════════════════════════════════════
    # RESULTS DASHBOARD
    # ════════════════════════════════════════

    n_verified     = sum(1 for r in results if r.verdict.status == VerdictStatus.VERIFIED)
    n_inaccurate   = sum(1 for r in results if r.verdict.status == VerdictStatus.INACCURATE)
    n_false        = sum(1 for r in results if r.verdict.status == VerdictStatus.FALSE)
    total = len(results)

    st.markdown("---")
    st.markdown('<div class="results-title">Verification Report</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="results-meta">{total} CLAIMS ANALYZED &nbsp;·&nbsp; TAVILY WEB SEARCH &nbsp;·&nbsp; GROK REASONING</div>',
        unsafe_allow_html=True,
    )

    # Tiles
    st.markdown(f"""
    <div class="tiles">
        <div class="tile"><div class="tile-num n-total">{total}</div><div class="tile-label">Analyzed</div></div>
        <div class="tile"><div class="tile-num n-verified">{n_verified}</div><div class="tile-label">Verified</div></div>
        <div class="tile"><div class="tile-num n-inaccurate">{n_inaccurate}</div><div class="tile-label">Inaccurate</div></div>
        <div class="tile"><div class="tile-num n-false">{n_false}</div><div class="tile-label">False</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Filter
    filter_opts = ["All", "Verified", "Inaccurate", "False"]
    sel = st.radio("Filter:", filter_opts, horizontal=True, label_visibility="collapsed")
    filter_map = {
        "All": None,
        "Verified": VerdictStatus.VERIFIED,
        "Inaccurate": VerdictStatus.INACCURATE,
        "False": VerdictStatus.FALSE,
    }
    filtered = [r for r in results if filter_map[sel] is None or r.verdict.status == filter_map[sel]]

    st.markdown(
        f'<div style="font-size:0.65rem;color:#2e2854;font-family:\'JetBrains Mono\',monospace;margin:0.8rem 0 1.4rem;">showing {len(filtered)} of {total}</div>',
        unsafe_allow_html=True,
    )

    # Cards
    for result in filtered:
        s = result.verdict.status
        card_cls  = {VerdictStatus.VERIFIED:"vcard-verified", VerdictStatus.INACCURATE:"vcard-inaccurate",
                     VerdictStatus.FALSE:"vcard-false"}.get(s, "vcard-false")
        badge_cls = {VerdictStatus.VERIFIED:"badge-verified", VerdictStatus.INACCURATE:"badge-inaccurate",
                     VerdictStatus.FALSE:"badge-false"}.get(s, "badge-false")

        sources_html = ""
        for url in result.verdict.sources[:3]:
            if url:
                safe_url = html.escape(url, quote=True)
                disp = html.escape(url.replace("https://","").replace("http://","")[:55])
                sources_html += f'<a class="src-link" href="{safe_url}" target="_blank">Source: {disp}</a>'

        correction_html = ""
        if result.verdict.corrected_fact:
            corrected_fact = html.escape(result.verdict.corrected_fact)
            correction_html = f"""
            <div class="correction-label">Corrected Fact</div>
            <div class="correction">{corrected_fact}</div>
            """

        claim_type = html.escape(get_claim_type_label(result.claim.claim_type))
        claim_text = html.escape(result.claim.text)
        reasoning = html.escape(result.verdict.reasoning)

        st.markdown(f"""
        <div class="vcard {card_cls}">
            <div class="vcard-type">{claim_type}</div>
            <div class="vcard-claim">"{claim_text}"</div>
            <div class="vcard-row">
                <span class="badge {badge_cls}">{s.value}</span>
                <span class="conf">Confidence: <b>{result.confidence_pct}%</b></span>
            </div>
            <div class="reasoning">{reasoning}</div>
            {correction_html}
            {('<div style="margin-top:0.4rem;">' + sources_html + '</div>') if sources_html else ''}
        </div>
        """, unsafe_allow_html=True)

    # Integrity Score
    score = int((n_verified / total) * 100) if total else 0
    score_color = "#10b981" if score >= 80 else "#f59e0b" if score >= 50 else "#ef4444"
    problems = n_inaccurate + n_false
    st.markdown("---")
    st.markdown(f"""
    <div class="score-wrap">
        <div class="score-label">Document Integrity Score</div>
        <div class="score-num" style="color:{score_color};">{score}<span class="score-unit">%</span></div>
        <div class="score-desc">{problems} problem{'s' if problems != 1 else ''} detected across {total} claims</div>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════

st.markdown("""
<div class="footer">
    Fact-Check Agent &nbsp;·&nbsp; Grok + Tavily &nbsp;·&nbsp; Built with Streamlit
</div>
""", unsafe_allow_html=True)
