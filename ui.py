"""Streamlit approval UI. Chalane ke liye: streamlit run ui.py"""
import time

import streamlit as st

from app.gmail_client import create_draft, fetch_unread, mark_processed
from app.graph import build_analysis_graph

st.set_page_config(page_title="Email Agent", page_icon="📧", layout="wide")
st.title("📧 Email Agent")
st.caption("Agent mails padhta hai, reply draft karta hai. Save tumhare approve karne par hi hota hai.")

if "items" not in st.session_state:
    st.session_state.items = []  # reply wali mails (approval pending)
if "ignored" not in st.session_state:
    st.session_state.ignored = []  # newsletter/spam jin par reply nahi chahiye


@st.cache_resource
def get_graph():
    return build_analysis_graph()


max_mails = st.sidebar.slider("Ek baar mein kitni mails", 1, 10, 5)

if st.button("Inbox check karo", type="primary"):
    graph = get_graph()
    with st.spinner("Mails fetch aur analyze ho rahi hain..."):
        mails = fetch_unread(max_results=max_mails)
        items, ignored = [], []
        for m in mails:
            out = graph.invoke({"mail": m})
            analysis = out["analysis"]
            if analysis.needs_reply:
                items.append({"mail": m, "analysis": analysis, "reply": out["reply"]})
            else:
                mark_processed(m["id"])  # reply nahi chahiye, to label laga do
                ignored.append({"mail": m, "analysis": analysis})
            time.sleep(1)  # Groq free tier rate limit
        st.session_state.items = items
        st.session_state.ignored = ignored
    if not mails:
        st.info("Koi nayi unread mail nahi mili.")

# ---- Reply wali mails ----
items = st.session_state.items
st.subheader(f"Reply wali mails ({len(items)})")
if not items:
    st.write("Abhi koi pending draft nahi.")

for item in list(items):
    m, a = item["mail"], item["analysis"]
    with st.container(border=True):
        st.markdown(f"**{m['subject']}**  \nFrom: {m['from']}  ·  `{a.category}`")
        st.caption(a.summary)
        with st.expander("Original mail"):
            st.text(m["body"][:1500])

        key = f"reply_{m['id']}"
        if key not in st.session_state:
            st.session_state[key] = item["reply"]
        st.text_area("Draft reply (edit kar sakti ho)", key=key, height=180)

        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("Save to Gmail Drafts", key=f"save_{m['id']}"):
            create_draft(m, st.session_state[key])
            mark_processed(m["id"])
            st.session_state.items = [i for i in st.session_state.items if i["mail"]["id"] != m["id"]]
            st.rerun()
        if c2.button("Skip", key=f"skip_{m['id']}"):
            mark_processed(m["id"])
            st.session_state.items = [i for i in st.session_state.items if i["mail"]["id"] != m["id"]]
            st.rerun()

# ---- Ignore ki hui mails ----
ignored = st.session_state.ignored
if ignored:
    with st.expander(f"Ignore ki gayi mails ({len(ignored)}), reply ki zaroorat nahi"):
        for it in ignored:
            st.write(f"**{it['mail']['subject']}**: {it['analysis'].category}, {it['analysis'].summary}")