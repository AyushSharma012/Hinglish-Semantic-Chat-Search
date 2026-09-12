"""
Enhanced Streamlit UI for Hinglish Semantic Chat Search.

Usage:
    streamlit run src/ui/streamlit_app.py
"""


from __future__ import annotations


import os
import sys
from pathlib import Path
from datetime import datetime


# Ensure project root is on PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import streamlit as st
import httpx


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
DEFAULT_TOP_K = 5
DEFAULT_CONTEXT_WINDOW = 3


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def call_search(query: str, top_k: int, context_window: int) -> dict:
    """Call the search API with timeout and error handling."""
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{API_BASE}/search",
            json={
                "query": query,
                "top_k": top_k,
                "context_window": context_window,
            },
        )
        resp.raise_for_status()
        return resp.json()


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y · %I:%M %p")
    except:
        return ts[:16] if ts else ""


def render_message(msg: dict, is_match: bool = False, show_sender: bool = True):
    """Render a single message with styling."""
    sender = msg.get("sender", "?")
    ts = msg.get("timestamp", "")
    text = msg.get("text", "")
    
    timestamp = format_timestamp(ts)
    
    if is_match:
        # Highlighted match with green background
        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
                        padding: 12px 16px; border-radius: 8px;
                        border-left: 4px solid #2e7d32; margin: 6px 0;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1)'>
                <div style='display: flex; justify-content: space-between; margin-bottom: 6px'>
                    <span style='font-weight: 600; color: #1b5e20'>⭐ {sender}</span>
                    <span style='font-size: 0.85em; color: #388e3c'>{timestamp}</span>
                </div>
                <div style='font-size: 1.05em; line-height: 1.5; color: #2e7d32'>{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Regular context message with subtle styling
        st.markdown(
            f"""
            <div style='padding: 8px 12px; margin: 4px 0;
                        border-left: 3px solid #e0e0e0;
                        background: #fafafa; border-radius: 4px'>
                <div style='display: flex; justify-content: space-between; margin-bottom: 4px'>
                    <span style='font-weight: 500; color: #424242'>{sender}</span>
                    <span style='font-size: 0.8em; color: #757575'>{timestamp}</span>
                </div>
                <div style='font-size: 0.95em; line-height: 1.4; color: #616161'>{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def check_backend_health() -> tuple[bool, dict]:
    """Check if backend API is healthy."""
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{API_BASE}/health")
            if resp.status_code == 200:
                return True, resp.json()
            return False, {}
    except:
        return False, {}


def render_result_card(res: dict, rank: int, max_rank: int):
    """Render a single result card with context."""
    score = res.get("score", 0)
    matched = res.get("matched_message", {})
    context = res.get("context", [])
    
    # Create a nice header for the expander
    sender = matched.get("sender", "?")
    timestamp = format_timestamp(matched.get("timestamp", ""))
    text_preview = matched.get("text", "")[:80]
    
    header = f"#{rank} · Score: {score:.3f} · {sender}"
    
    # Expand only the top result or if there are few results
    expand = (rank == 1) or (max_rank <= 2)
    
    with st.expander(header, expanded=expand):
        # Show context messages
        if context:
            st.markdown("**Conversation Context:**")
            for msg in context:
                is_match = msg.get("is_match", False) or (msg.get("msg_id") == matched.get("msg_id"))
                render_message(msg, is_match=is_match)
        else:
            # No context, just show the matched message
            render_message(matched, is_match=True)
        
        # Show metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rank", rank)
        with col2:
            st.metric("Score", f"{score:.3f}")
        with col3:
            st.metric("Message ID", matched.get("msg_id", "?"))


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Hinglish Semantic Chat Search",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5em;
            font-weight: 700;
            background: linear-gradient(90deg, #1976d2, #42a5f5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5em;
        }
        .sub-header {
            font-size: 1.1em;
            color: #616161;
            margin-bottom: 1.5em;
        }
        .stExpander {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 12px;
        }
        .stats-box {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 15px 20px;
            border-radius: 10px;
            margin: 10px 0;
            border: 1px solid #e0e0e0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="main-header">💬 Hinglish Semantic Chat Search</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        'Search by <b>meaning</b>, not just keywords. '
        'Supports English, Hindi & Hinglish. '
        'You can mention people or time (last month, yesterday, etc.).'
        '</div>',
        unsafe_allow_html=True,
    )
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        top_k = st.slider(
            "Top-K results",
            min_value=1,
            max_value=15,
            value=DEFAULT_TOP_K,
            help="Number of top results to show",
        )
        
        context_window = st.slider(
            "Context window (±N)",
            min_value=0,
            max_value=8,
            value=DEFAULT_CONTEXT_WINDOW,
            help="Show N messages before and after each match",
        )
        
        st.markdown("---")
        
        # Backend health check
        st.subheader("🔌 Backend Status")
        is_healthy, health_data = check_backend_health()
        
        if is_healthy:
            st.success("✅ Backend connected")
            msg_count = health_data.get("message_count", 0)
            idx_count = health_data.get("index_count", 0)
            st.caption(f"Messages: {msg_count:,} | Indexed: {idx_count:,}")
        else:
            st.error("❌ Backend unavailable")
            st.caption("Make sure the FastAPI backend is running")
        
        st.markdown("---")
        
        # Project stats
        st.subheader("📊 Corpus Stats")
        st.markdown(
            """
            <div class='stats-box'>
                <div style='font-size: 0.9em'>
                    <b>Messages:</b> 4,200+<br>
                    <b>Participants:</b> 8<br>
                    <b>Time Span:</b> 6 months<br>
                    <b>Decision Threads:</b> 3<br>
                    <b>Test Queries:</b> 40 (8 hard)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        st.markdown("---")
        
        # Example queries
        st.subheader("💡 Example Queries")
        
        examples = {
            "Meaning-based": [
                "When did we decide on the trip?",
                "What was the final budget?",
                "chalo Manali fix hai kab hua?",
            ],
            "Person-based": [
                "What did Priya say about the budget?",
                "Amit ne budget ke baare me kya kaha?",
                "What did Rahul say about Manali?",
            ],
            "Time-based": [
                "What did we discuss last month?",
                "Budget wali baat kab hui thi?",
                "last week mein kya decide hua?",
            ],
            "Hinglish": [
                "hotel ka naam kya final hua?",
                "flight book ho gayi kya?",
                "45k per person decide hua tha?",
            ],
        }
        
        for category, queries in examples.items():
            with st.expander(category, expanded=False):
                for q in queries:
                    if st.button(q, key=f"ex_{q[:20]}", use_container_width=True):
                        st.session_state["example_query"] = q
                        st.rerun()
        
        st.markdown("---")
        
        # Info
        st.info(
            """
            **About This Project**
            
            This system uses semantic embeddings to understand meaning, not just keywords.
            It can find messages even when the query and answer share zero words!
            
            **Tech Stack:**
            - Embeddings: paraphrase-multilingual-MiniLM-L12-v2
            - Vector DB: ChromaDB
            - Backend: FastAPI
            - Frontend: Streamlit
            """
        )
    
    # Search box
    st.markdown("### 🔍 Search Conversations")
    
    # Check if example was clicked
    if "example_query" in st.session_state:
        default_query = st.session_state["example_query"]
        del st.session_state["example_query"]
    else:
        default_query = ""
    
    query = st.text_input(
        "Search conversations",
        value=default_query,
        placeholder="e.g., When did we decide on the trip? | What did Priya say about budget? | chalo Manali fix hai kab hua?",
        label_visibility="collapsed",
        key="query_input",
    )
    
    # Search button row
    col1, col2 = st.columns([4, 1])
    with col1:
        search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)
    
    # Auto-search on Enter (when query changes)
    if query and st.session_state.get("last_query") != query:
        st.session_state["last_query"] = query
        search_clicked = True
    
    # Process search
    if search_clicked and query.strip():
        st.session_state["last_query"] = query
        
        with st.spinner("🔎 Searching conversations..."):
            try:
                data = call_search(query.strip(), top_k, context_window)
            except Exception as e:
                st.error(f"❌ Could not reach the search service: {e}")
                st.info("💡 Make sure the FastAPI backend is running: `python -m src.api.main`")
                return
        
        # Display query
        st.markdown(f"**Query:** `{data.get('query', query)}`")
        
        # Show filter notice if any
        if data.get("filter_notice"):
            st.warning(f"ℹ️ {data['filter_notice']}", icon="ℹ️")
        
        # Handle different statuses
        status = data.get("status")
        
        if status == "no_matches":
            st.info(
                "🔍 **No matches found.**\n\n"
                "Try:\n"
                "- Rephrasing your query\n"
                "- Using different keywords\n"
                "- Removing person/time constraints\n"
                "- Using Hinglish or Hindi terms",
                icon="ℹ️",
            )
            return
        
        if status == "error":
            st.error(f"❌ {data.get('message', 'Unable to process query.')}")
            return
        
        # Show results
        results = data.get("results", [])
        
        if not results:
            st.info("🔍 No matches found.", icon="ℹ️")
            return
        
        st.success(f"✅ Found **{len(results)}** result(s)", icon="✅")
        
        # Display results
        st.markdown("### 📋 Results")
        
        for i, res in enumerate(results, 1):
            render_result_card(res, rank=i, max_rank=len(results))
        
        # Performance metrics
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Top-K", top_k)
        with col2:
            st.metric("Context Window", f"±{context_window}")
        with col3:
            st.metric("Results", len(results))
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #757575; font-size: 0.9em; padding: 20px 0'>
            <b>Hinglish Semantic Chat Search</b> · 
            Powered by semantic embeddings · 
            Supports English, Hindi & Hinglish<br>
            <small>Built with FastAPI + ChromaDB + Streamlit</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()