"""Streamlit approval UI. Chalane ke liye: streamlit run ui.py"""
import time

import streamlit as st

from app.gmail_client import create_draft, fetch_unread, mark_processed
from app.graph import build_analysis_graph

st.set_page_config(page_title="Email Agent", page_icon="📧", layout="wide")
st.title("📧 Email Agent")
st.caption("Agent mails padhta hai, reply draft karta hai. Save tumhare approve karne par hi hota hai.")

# NOTE: "items" naam mat rakhna, session_state.items dict ka built-in method hai
if "pending" not in st.session_state:
    st.session_state["pending"] = []  # reply wali mails (approval pending)
if "skipped_mails" not in st.session_state:
    st.session_state["skipped_mails"] = []  # newsletter/spam jin par reply nahi chahiye


@st.cache_resource
def get_graph():
    return build_analysis_graph()


max_mails = st.sidebar.slider("Ek baar mein kitni mails", 1, 10, 5)

if st.button("Inbox check karo", type="primary"):
    graph = get_graph()
    with st.spinner("Mails fetch aur analyze ho rahi hain..."):
        mails = fetch_unread(max_results=max_mails)
        pending, skipped = [], []
        for m in mails:
            out = graph.invoke({"mail": m})
            analysis = out["analysis"]
            if analysis.needs_reply:
                pending.append({"mail": m, "analysis": analysis, "reply": out["reply"]})
            else:
                mark_processed(m["id"])  # reply nahi chahiye, to label laga do
                skipped.append({"mail": m, "analysis": analysis})
            time.sleep(1)  # Groq free tier rate limit
        st.session_state["pending"] = pending
        st.session_state["skipped_mails"] = skipped
    if not mails:
        st.info("Koi nayi unread mail nahi mili.")

# ---- Reply wali mails ----
pending = st.session_state["pending"]
st.subheader(f"Reply wali mails ({len(pending)})")
if not pending:
    st.write("Abhi koi pending draft nahi.")

for item in list(pending):
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
            st.session_state["pending"] = [
                i for i in st.session_state["pending"] if i["mail"]["id"] != m["id"]
            ]
            st.rerun()
        if c2.button("Skip", key=f"skip_{m['id']}"):
            mark_processed(m["id"])
            st.session_state["pending"] = [
                i for i in st.session_state["pending"] if i["mail"]["id"] != m["id"]
            ]
            st.rerun()

# ---- Ignore ki hui mails ----
skipped = st.session_state["skipped_mails"]
if skipped:
    with st.expander(f"Ignore ki gayi mails ({len(skipped)}), reply ki zaroorat nahi"):
        for it in skipped:
            st.write(f"**{it['mail']['subject']}**: {it['analysis'].category}, {it['analysis'].summary}")