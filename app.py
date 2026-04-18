import streamlit as st
import requests
import os

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="YT Insight",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

API_BASE = "http://localhost:8000"

# ── Custom CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500&display=swap');

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: #080810;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Hide streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 3rem 3rem; max-width: 1100px; }

/* ── Hero title ── */
.hero {
    text-align: center;
    padding: 3rem 0 2rem 0;
}
.hero h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 3.8rem;
    letter-spacing: -2px;
    background: linear-gradient(135deg, #ff4d6d 0%, #ff9a3c 50%, #ffcc02 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    line-height: 1;
}
.hero p {
    color: #555570;
    font-size: 0.85rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 0.8rem;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Input card ── */
.input-card {
    background: #0e0e1a;
    border: 1px solid #1e1e35;
    border-radius: 16px;
    padding: 2rem;
    margin-bottom: 2rem;
}

/* ── Mode tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0e0e1a;
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
    border: 1px solid #1e1e35;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: #555570;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    font-size: 0.9rem;
    padding: 10px 24px;
    border: none;
    letter-spacing: 0.5px;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #ff4d6d, #ff9a3c) !important;
    color: white !important;
}

/* ── Text input ── */
.stTextInput > div > div > input {
    background: #12121f !important;
    border: 1px solid #2a2a45 !important;
    border-radius: 10px !important;
    color: #e0e0ff !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.9rem !important;
    padding: 14px 16px !important;
    transition: border-color 0.2s;
}
.stTextInput > div > div > input:focus {
    border-color: #ff4d6d !important;
    box-shadow: 0 0 0 2px rgba(255, 77, 109, 0.15) !important;
}
.stTextInput label {
    color: #555570 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #ff4d6d 0%, #ff9a3c 100%);
    color: white;
    border: none;
    border-radius: 10px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.95rem;
    padding: 12px 32px;
    width: 100%;
    letter-spacing: 1px;
    transition: opacity 0.2s, transform 0.1s;
    cursor: pointer;
}
.stButton > button:hover {
    opacity: 0.88;
    transform: translateY(-1px);
}
.stButton > button:active {
    transform: translateY(0px);
}

/* ── Result box ── */
.result-box {
    background: #0e0e1a;
    border: 1px solid #1e1e35;
    border-left: 3px solid #ff4d6d;
    border-radius: 12px;
    padding: 1.8rem;
    color: #c8c8e8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.88rem;
    line-height: 1.8;
    white-space: pre-wrap;
    margin-top: 1.5rem;
}

/* ── Status tags ── */
.tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-weight: 500;
    margin-bottom: 1rem;
}
.tag-success { background: rgba(39,174,96,0.15); color: #27ae60; border: 1px solid rgba(39,174,96,0.3); }
.tag-error   { background: rgba(231,76,60,0.15);  color: #e74c3c; border: 1px solid rgba(231,76,60,0.3); }
.tag-info    { background: rgba(52,152,219,0.15); color: #3498db; border: 1px solid rgba(52,152,219,0.3); }

/* ── Divider ── */
.divider {
    border: none;
    border-top: 1px solid #1a1a2e;
    margin: 1.5rem 0;
}

/* ── Spinner override ── */
.stSpinner > div { border-top-color: #ff4d6d !important; }

/* ── Mindmap iframe ── */
.mindmap-frame {
    border: 1px solid #1e1e35;
    border-radius: 12px;
    overflow: hidden;
    margin-top: 1.5rem;
}

/* ── Section label ── */
.section-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.72rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #ff4d6d;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>YT MIND </h1>
    <p>RAG · Summary · Mindmap — By Dil_Jain</p>
</div>
""", unsafe_allow_html=True)

from urllib.parse import urlparse, parse_qs
def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    
    # Handle youtu.be/xxx short links
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path.lstrip("/").split("?")[0]
    
    # Handle youtube.com/watch?v=xxx&t=56s  ← your problem case
    video_id = parse_qs(parsed.query).get("v", [None])[0]
    
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    return video_id
# ── Video ID input ───────────────────────────────────────────────────
st.markdown('<div class="input-card">', unsafe_allow_html=True)
st.markdown('<div class="section-label">YouTube Video ID</div>', unsafe_allow_html=True)
video_link = st.text_input(
    label="video_id",
    placeholder="e.g. https://www.youtube.com/watch?v=-4e3ewcTupM&t=4s",
    label_visibility="collapsed"
)

if video_link:
    video_id=extract_video_id(video_link)
st.markdown('</div>', unsafe_allow_html=True)

# ── Mode tabs ────────────────────────────────────────────────────────
tab_rag, tab_summary, tab_mindmap = st.tabs(["🔍 RAG", "📝 Summary", "🧠 Mindmap"])


# ════════════════════════════════════════════════════════════════════
# TAB 1 — RAG
# ════════════════════════════════════════════════════════════════════
with tab_rag:
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">Your Question</div>', unsafe_allow_html=True)
    query = st.text_input(
        label="query",
        placeholder=" e.g What is covered in this video ? ",
        label_visibility="collapsed",
        key="rag_query"
    )

    if st.button("Get Answer", key="rag_btn"):
        if not video_id:
            st.markdown('<span class="tag tag-error">⚠ Enter a Video ID first</span>', unsafe_allow_html=True)
        elif not query:
            st.markdown('<span class="tag tag-error">⚠ Enter a question</span>', unsafe_allow_html=True)
        else:
            with st.spinner("Searching through transcript..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/rag",
                        data={"video_id": video_id, "query": query},
                        timeout=120
                    )
                    if resp.status_code == 200:
                        answer = resp.json().get("answer", "No answer returned.")
                        st.markdown('<span class="tag tag-success">✓ Answer ready</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="result-box">{answer}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="tag tag-error">API Error {resp.status_code}</span>', unsafe_allow_html=True)
                        st.code(resp.text)
                except requests.exceptions.ConnectionError:
                    st.markdown('<span class="tag tag-error">⚠ Cannot connect to API — is uvicorn running?</span>', unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<span class="tag tag-error">Error: {e}</span>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════
# TAB 2 — SUMMARY
# ════════════════════════════════════════════════════════════════════
with tab_summary:
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#555570; font-size:0.82rem; font-family:\'JetBrains Mono\',monospace;">'
        'No query needed — just provide the Video ID above and hit Generate.</p>',
        unsafe_allow_html=True
    )

    if st.button("Generate Summary", key="summary_btn"):
        if not video_id:
            st.markdown('<span class="tag tag-error">⚠ Enter a Video ID first</span>', unsafe_allow_html=True)
        else:
            with st.spinner("Summarizing transcript chunks..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/summary",
                        data={"video_id": video_id},
                        timeout=300
                    )
                    if resp.status_code == 200:
                        summary = resp.json().get("summary", "No summary returned.")
                        st.markdown('<span class="tag tag-success">✓ Summary ready</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="result-box">{summary}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="tag tag-error">API Error {resp.status_code}</span>', unsafe_allow_html=True)
                        st.code(resp.text)
                except requests.exceptions.ConnectionError:
                    st.markdown('<span class="tag tag-error">⚠ Cannot connect to API — is uvicorn running?</span>', unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<span class="tag tag-error">Error: {e}</span>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════
# TAB 3 — MINDMAP
# ════════════════════════════════════════════════════════════════════
with tab_mindmap:
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#555570; font-size:0.82rem; font-family:\'JetBrains Mono\',monospace;">'
        'Generates an interactive visual mindmap from the video transcript.</p>',
        unsafe_allow_html=True
    )

    if st.button("Generate Mindmap", key="mindmap_btn"):
        if not video_id:
            st.markdown('<span class="tag tag-error">⚠ Enter a Video ID first</span>', unsafe_allow_html=True)
        else:
            with st.spinner("Extracting topics and building mindmap..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/mindmap",
                        data={"video_id": video_id},
                        timeout=300
                    )
                    if resp.status_code == 200:
                        # Save HTML returned from API
                        html_content = resp.text
                        mindmap_path = "mindmap_result.html"
                        with open(mindmap_path, "w", encoding="utf-8") as f:
                            f.write(html_content)

                        st.markdown('<span class="tag tag-success">✓ Mindmap ready</span>', unsafe_allow_html=True)

                        # Render inline
                        st.markdown('<div class="mindmap-frame">', unsafe_allow_html=True)
                        st.components.v1.html(html_content, height=650, scrolling=False)
                        st.markdown('</div>', unsafe_allow_html=True)

                        # Download button
                        st.download_button(
                            label="⬇ Download Mindmap HTML..",
                            data=html_content,
                            file_name="mindmap.html",
                            mime="text/html"
                        )
                    else:
                        st.markdown(f'<span class="tag tag-error">API Error {resp.status_code}</span>', unsafe_allow_html=True)
                        st.code(resp.text)
                except requests.exceptions.ConnectionError:
                    st.markdown('<span class="tag tag-error">⚠ Cannot connect to API — is uvicorn running?</span>', unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<span class="tag tag-error">Error: {e}</span>', unsafe_allow_html=True)