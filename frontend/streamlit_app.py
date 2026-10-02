"""
Streamlit Chat UI for MF FAQ Assistant.

Run with:
    streamlit run frontend/streamlit_app.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
import streamlit as st
import requests
import uuid
import subprocess
import sys
import time

from ingestion.embedder import get_chroma_collection
from ingestion.ingest import run_ingestion_pipeline

def ensure_chroma_data():
    """Ensure ChromaDB is populated before starting the API."""
    try:
        collection = get_chroma_collection()
        count = collection.count()

        if count == 0:
            st.info("Initializing knowledge base...")
            success = run_ingestion_pipeline(force=False)

            if not success:
                st.error("Failed to initialize the knowledge base.")
                st.stop()

            count = get_chroma_collection().count()

        print(f"ChromaDB ready with {count} chunks")

    except Exception as e:
        st.error(f"Failed to initialize ChromaDB: {e}")
        st.stop()

@st.cache_resource
def start_api_server():
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
    )

    # Give FastAPI time to initialize
    for _ in range(30):
        try:
            response = requests.get(
                "http://127.0.0.1:8000/health",
                timeout=2,
            )
            if response.status_code == 200:
                return process
        except requests.exceptions.RequestException:
            time.sleep(1)

    return process


ensure_chroma_data()
api_process = start_api_server()
# =============================================================================
# Config
# =============================================================================

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="MF FAQ Assistant",
    page_icon="📊",
    layout="centered",
)

# =============================================================================
# Session State
# =============================================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.title("MF FAQ Assistant")
    st.markdown("Facts-only mutual fund information")
    st.markdown("---")

    # Clear chat button
    if st.button("Clear Chat", type="primary"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

        st.markdown("---")

    st.markdown("### Example Questions")
    examples = [
        "What is the expense ratio of HDFC Large Cap Fund?",
        "What is the ELSS lock-in period?",
        "What is the minimum SIP for HDFC Small Cap Fund?",
        "What is the benchmark of HDFC Equity Fund?",
    ]

    for ex in examples:
        if st.button(ex):
            st.session_state.pending_question = ex
            st.rerun()

    st.markdown("---")
    st.markdown("**Facts-only. No investment advice.**")
# =============================================================================
# Header
# =============================================================================

st.title("MF FAQ Assistant")
st.markdown("Ask factual questions about HDFC mutual fund schemes.")

# =============================================================================
# Chat Messages
# =============================================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Show sources expander for assistant messages
        if message["role"] == "assistant" and "sources" in message:
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.markdown(f"- [{source}]({source})")

# =============================================================================
# Chat Input
# =============================================================================

prompt = st.session_state.pop("pending_question", None) or st.chat_input("Ask a question...")

if prompt:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get answer from API
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/ask",
                    json={
                        "question": prompt,
                        "session_id": st.session_state.session_id,
                    },
                    timeout=30,
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "No answer generated.")
                    sources = data.get("sources", [])

                    st.markdown(answer)

                    # Store message with sources
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                        }
                    )

                    # Show sources expander
                    with st.expander("Sources"):
                        for source in sources:
                            st.markdown(f"- [{source}]({source})")

                else:
                    error_data = response.json()
                    error_msg = error_data.get("detail", {}).get("error", "An error occurred.")
                    st.error(error_msg)

                    st.session_state.messages.append(
                        {"role": "assistant", "content": f"Error: {error_msg}"}
                    )

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to API server. Make sure it's running at localhost:8000")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
st.markdown(
    "<small><strong>Facts-only. No investment advice.</strong> "
    "This assistant provides factual information from official sources only. "
    "It does not recommend any scheme or provide investment advice. "
    "Please consult a SEBI-registered investment advisor before making investment decisions.</small>",
    unsafe_allow_html=True,
)
