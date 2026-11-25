"""Streamlit approval UI. Run with: streamlit run ui.py"""
import time

import streamlit as st

from app.gmail_client import (
    create_draft,
    fetch_unread,
    mark_processed,
    reply_address,
    send_reply,
)
from app.graph import build_analysis_graph

st.set_page_config(page_title="Email Agent", page_icon="📧", layout="wide")
st.title("📧 Email Agent")
st.caption("The agent reads your mails and drafts replies. Nothing is sent or saved until you approve it.")

# NOTE: don't name a key "items": st.session_state.items is a built-in dict method
if "pending" not in st.session_state:
    st.session_state["pending"] = []  # mails that need a reply (waiting for approval)
if "skipped_mails" not in st.session_state:
    st.session_state["skipped_mails"] = []  # newsletters/spam that need no reply


@st.cache_resource
def get_graph():
    return build_analysis_graph()


max_mails = st.sidebar.slider("Mails to check per run", 1, 10, 5)

if st.button("Check inbox", type="primary"):
    graph = get_graph()
    with st.spinner("Fetching and analyzing mails..."):
        mails = fetch_unread(max_results=max_mails)
        pending, skipped = [], []
        for m in mails:
            out = graph.invoke({"mail": m})
            analysis = out["analysis"]
            if analysis.needs_reply:
                pending.append({"mail": m, "analysis": analysis, "reply": out["reply"]})
            else:
                mark_processed(m["id"])  # no reply needed, so label it as handled
                skipped.append({"mail": m, "analysis": analysis})
            time.sleep(1)  # Groq free tier rate limit
        st.session_state["pending"] = pending
        st.session_state["skipped_mails"] = skipped
    if not mails:
        st.info("No new unread mails found.")

# ---- Mails that need a reply ----
pending = st.session_state["pending"]
st.subheader(f"Mails needing a reply ({len(pending)})")
if not pending:
    st.write("No pending drafts right now.")

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
        st.text_area("Draft reply (you can edit it)", key=key, height=180)

        confirm_key = f"confirm_{m['id']}"
        c1, c2, c3, _ = st.columns([1, 1.4, 1, 3])

        if c1.button("Send reply", key=f"send_{m['id']}", type="primary"):
            st.session_state[confirm_key] = True  # ask for confirmation first
            st.rerun()

        if c2.button("Save to Gmail Drafts", key=f"save_{m['id']}"):
            create_draft(m, st.session_state[key])
            mark_processed(m["id"])
            st.session_state["pending"] = [
                i for i in st.session_state["pending"] if i["mail"]["id"] != m["id"]
            ]
            st.rerun()

        if c3.button("Skip", key=f"skip_{m['id']}"):
            mark_processed(m["id"])
            st.session_state["pending"] = [
                i for i in st.session_state["pending"] if i["mail"]["id"] != m["id"]
            ]
            st.rerun()

        # Second confirmation so a reply is never sent by accident
        if st.session_state.get(confirm_key):
            st.warning(f"This will send the reply to **{reply_address(m)}** right now.")
            y, n, _ = st.columns([1, 1, 4])
            if y.button("Yes, send", key=f"yes_{m['id']}", type="primary"):
                send_reply(m, st.session_state[key])
                mark_processed(m["id"])
                st.session_state["pending"] = [
                    i for i in st.session_state["pending"] if i["mail"]["id"] != m["id"]
                ]
                st.session_state.pop(confirm_key, None)
                st.rerun()
            if n.button("Cancel", key=f"cancel_{m['id']}"):
                st.session_state[confirm_key] = False
                st.rerun()

# ---- Mails that were ignored ----
skipped = st.session_state["skipped_mails"]
if skipped:
    with st.expander(f"Ignored mails ({len(skipped)}), no reply needed"):
        for it in skipped:
            st.write(f"**{it['mail']['subject']}**: {it['analysis'].category}, {it['analysis'].summary}")