import streamlit as st
import os, json, re
from openai import OpenAI

# ➕ BATCH IMPORTS
import pandas as pd
import io
import zipfile
from datetime import datetime


st.set_page_config(
    page_title="GEOG — Free Interpreter",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  (TON CSS INCHANGÉ)
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ===================== TON CSS INCHANGÉ ===================== */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
.stApp { background:#0e1117; color:#e2e8f0; }

/* ... TOUT TON CSS RESTE IDENTIQUE ... */
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  MODE SWITCH (NEW)
# ─────────────────────────────────────────────
mode = st.radio("Mode", ["Single", "Batch (CSV)"])

# ─────────────────────────────────────────────
#  CLIENT
# ─────────────────────────────────────────────
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    st.error("🔑 Missing GROQ_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url="https://api.groq.com/openai/v1")

# ─────────────────────────────────────────────
#  SAFE JSON
# ─────────────────────────────────────────────
def safe_json(text: str) -> dict:
    if not text:
        return {}
    clean = re.sub(r"```(?:json)?", "", text).strip(" `\n")
    for candidate in [clean, text]:
        try:
            return json.loads(candidate)
        except:
            pass
        m = re.search(r"\{.*\}", candidate, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except:
                pass
    return {}

# ─────────────────────────────────────────────
#  PROMPT
# ─────────────────────────────────────────────
PROMPT = """You are a geophysics expert...
{text}
"""

# ─────────────────────────────────────────────
#  PIPELINE
# ─────────────────────────────────────────────
def run_pipeline(text: str) -> dict:
    prompt = PROMPT.replace("{text}", text)

    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    data = safe_json(r.choices[0].message.content)

    # --- garde TOUT ton pipeline intact ---
    return data

# ─────────────────────────────────────────────
#  UI HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="geog-header">
  <div class="geog-globe">🌍</div>
  <div class="chip">FREE INTERPRETER</div>
  <h1>GEOG — Free Interpreter</h1>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  =========================
#  SINGLE MODE (EXISTANT)
#  =========================
# ─────────────────────────────────────────────
if mode == "Single":

    st.markdown('<div class="slabel">Your Description</div>', unsafe_allow_html=True)

    text = st.text_area(
        "",
        placeholder="Write anything...",
        height=140,
        label_visibility="collapsed",
    )

    run = st.button("▶ INTERPRET")

    if run and text.strip():

        with st.spinner("Interpreting…"):
            data = run_pipeline(text)

        st.json(data)

# ─────────────────────────────────────────────
#  =========================
#  BATCH MODE (NEW)
#  =========================
# ─────────────────────────────────────────────
if mode == "Batch (CSV)":

    st.markdown('<div class="slabel">Batch Mode</div>', unsafe_allow_html=True)

    file = st.file_uploader("Upload CSV", type=["csv"])

    column = st.text_input("Column name", value="text")

    run_batch = st.button("▶ RUN BATCH")

    if file and run_batch:

        df = pd.read_csv(file)

        if column not in df.columns:
            st.error(f"Column '{column}' not found")
            st.stop()

        zip_buffer = io.BytesIO()

        results_log = []

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:

            progress = st.progress(0)
            total = len(df)

            for i, row in df.iterrows():

                text_input = str(row[column])

                try:
                    data = run_pipeline(text_input)

                    json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

                    zipf.writestr(f"geog_{i:04d}.json", json_bytes)

                    results_log.append({"i": i, "status": "ok"})

                except Exception as e:
                    results_log.append({"i": i, "status": "error", "err": str(e)})

                progress.progress((i + 1) / total)

        zip_buffer.seek(0)

        st.success("Batch completed")

        st.download_button(
            "⬇ Download ZIP",
            data=zip_buffer,
            file_name=f"geog_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
        )

        with st.expander("Batch log"):
            st.json(results_log)