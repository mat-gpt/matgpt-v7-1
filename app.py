# Mat-GPT v7.0 - Final Release
# Main Streamlit Application File

import streamlit as st
import pandas as pd
import sqlite3
import os
import base64
from db import init_db, get_memory_prompts, get_test_registry

st.set_page_config(page_title="Mat-GPT v7.0", layout="wide")

# Load Assistant Prompts from DB
conn = init_db()
prompts = get_memory_prompts(conn)

# Persistent Session State Init
if "history" not in st.session_state:
    st.session_state.history = []

if "test_registry" not in st.session_state:
    st.session_state.test_registry = get_test_registry(conn)

# Sidebar
with st.sidebar:
    st.title("🛰️ Mat-GPT v7.0")
    st.markdown("**Mode:** Satcom Test Intelligence")
    st.markdown("**Theme:** Padres / Chargers")
    st.markdown("**Build:** Feature Locked ✅")
    st.markdown("---")
    uploaded_files = st.file_uploader("Upload CSV, PCAP, or Log Files", accept_multiple_files=True)

    if uploaded_files:
        for file in uploaded_files:
            st.success(f"Uploaded: {file.name}")

# Main Chat Interface
st.title("Mat-GPT")
user_input = st.text_input("Ask Mat-GPT something about your test data:")

if user_input:
    st.session_state.history.append(("You", user_input))
    response = f"[Simulated Response] You asked: {user_input}"
    st.session_state.history.append(("Mat-GPT", response))

# Display Chat
for speaker, msg in st.session_state.history:
    if speaker == "You":
        st.markdown(f"**🧑 You:** {msg}")
    else:
        st.markdown(f"**🤖 Mat-GPT:** {msg}")

# Test Registry Viewer
st.markdown("---")
st.subheader("📋 Test Registry")
if st.session_state.test_registry is not None:
    st.dataframe(st.session_state.test_registry)
else:
    st.warning("No tests loaded in registry.")

conn.close()
