# Mat-GPT v6.9.1 — AI Assistant (Streaming Preview Fix)

import streamlit as st
import sqlite3
import openai
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ===============
# Session Defaults
# ===============
def init_session():
    defaults = {
        "username": None, "is_admin": False, "apikey": None,
        "theme": "Slam Diego (Padres Mode)", "model": "gpt-4o",
        "loading": False, "response": "", "chat": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session()

# ===============
# Database Setup
# ===============
conn = sqlite3.connect("matgpt.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    apikey TEXT,
    model TEXT,
    theme TEXT,
    isadmin INTEGER
)''')
conn.commit()

# ===============
# Theme Engine
# ===============
def apply_theme(theme):
    themes = {
        "Slam Diego (Padres Mode)": ".stApp { background-color: #DCCBA5; color: #2F2617; } .stSidebar { background-color: #4A3624 !important; color: #FCD581; } .stButton>button { background-color: #D6A419 !important; color: black; }",
        "Bolt Mode (Chargers)": ".stApp { background-color: #ECF7FF; color: #002244; } .stSidebar { background-color: #0073CF !important; color: #FFC20E; } .stButton>button { background-color: #FFC20E !important; color: #002244; }",
        "Arizona Cardinals": ".stApp { background-color: #A71930; color: white; } .stSidebar { background-color: #000000 !important; color: #FFFFFF; }",
        "Glasgow Rangers": ".stApp { background-color: #0033A0; color: white; } .stSidebar { background-color: #FFFFFF !important; color: #0033A0; }",
        "San Diego FC": ".stApp { background-color: #C320AE; color: white; } .stSidebar { background-color: #002147 !important; color: #00E6E6; }",
        "Yankees": ".stApp { background-color: #132448; color: white; background-image: repeating-linear-gradient(90deg, #132448, #132448 10px, white 10px, white 11px); } .stSidebar { background-color: #FFFFFF !important; color: #132448; }",
        "USA": ".stApp { background-color: white; background-image: url('https://upload.wikimedia.org/wikipedia/commons/0/09/Bald_Eagle_Portrait.jpg'); background-size: cover; color: navy; } .stSidebar { background-color: red !important; color: white; }"
    }
    if theme in themes:
        st.markdown(f"<style>{themes[theme]}</style>", unsafe_allow_html=True)

# ===============
# Login
# ===============
if not st.session_state.username:
    st.title("🔐 Login to Mat-GPT")
    uname = st.text_input("Username")
    pword = st.text_input("Password", type="password")
    theme_choice = st.selectbox("Theme", [
        "Slam Diego (Padres Mode)", "Bolt Mode (Chargers)",
        "Arizona Cardinals", "Glasgow Rangers",
        "San Diego FC", "Yankees", "USA"
    ])
    if st.button("Login"):
        user = cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (uname, pword)).fetchone()
        if user:
            st.session_state.username = user[0]
            st.session_state.apikey = user[2]
            st.session_state.model = user[3]
            st.session_state.theme = user[4] or theme_choice
            st.session_state.is_admin = user[5] == 1
            st.rerun()
        else:
            st.error("Login failed")
    st.stop()

apply_theme(st.session_state.theme)

# ===============
# Sidebar
# ===============
themes = [
    "Slam Diego (Padres Mode)", "Bolt Mode (Chargers)",
    "Arizona Cardinals", "Glasgow Rangers",
    "San Diego FC", "Yankees", "USA"
]
if st.session_state.theme not in themes:
    st.session_state.theme = themes[0]

st.sidebar.title("🌐 Theme")
st.sidebar.selectbox("", themes, index=themes.index(st.session_state.theme), key="theme", on_change=lambda: st.rerun())

if st.sidebar.button("🚪 Logout"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

if st.session_state.is_admin:
    with st.sidebar.expander("⚙ Admin Tools"):
        st.markdown("### Create New User")
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        new_apikey = st.text_input("API Key")
        new_model = st.selectbox("Default Model", ["gpt-4", "gpt-4o", "gpt-3.5-turbo"])
        new_theme = st.selectbox("Default Theme", themes)
        isadmin = st.checkbox("Admin Privileges")
        if st.button("Create User"):
            try:
                cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (new_username, new_password, new_apikey, new_model, new_theme, int(isadmin)))
                conn.commit()
                st.success(f"✅ User '{new_username}' created.")
            except sqlite3.IntegrityError:
                st.error("🚫 User already exists!")

        st.markdown("### Delete User")
        usernames = [u[0] for u in cursor.execute("SELECT username FROM users").fetchall() if u[0] != st.session_state.username]
        user_to_delete = st.selectbox("Select User to Delete", usernames)
        if st.button("Delete User"):
            cursor.execute("DELETE FROM users WHERE username = ?", (user_to_delete,))
            conn.commit()
            st.warning(f"❌ Deleted user: {user_to_delete}")

with st.sidebar.expander("🛠 Advanced Tools"):
    st.markdown("### 📂 CSV Parser (upload)")
    st.file_uploader("Upload CSV for Parsing", type="csv")
    st.markdown("### ⚡ Certus Selector")
    option = st.selectbox("Data Need?", ["Short bursts", "Long sustained", "Latency-sensitive"])
    if option == "Short bursts":
        st.info("Recommended device: SkyLink Certus 100")

# ===============
# Header
# ===============
st.markdown("""
    <div style='display: flex; justify-content: space-between;'>
        <h1>🤖 Mat-GPT v6.9.1 — Welcome {}</h1>
        <div style='font-size: 14px; margin-top: 30px;'>
            <b>Theme:</b> {}<br><b>Model:</b> {}
        </div>
    </div>
""".format(st.session_state.username, st.session_state.theme, st.session_state.model), unsafe_allow_html=True)

# ===============
# Chat Interface
# ===============
st.markdown("---")
st.markdown("### 💬 Mat-GPT Conversation")
for q, a in reversed(st.session_state.chat):
    st.markdown(f"**You:** {q}")
    st.markdown(f"**Mat-GPT:** {a}", unsafe_allow_html=True)

user_prompt = st.text_input("💬 Ask Mat-GPT", key="chat_input")
if st.button("📨 Send"):
    if not st.session_state.apikey:
        st.session_state.chat.append((user_prompt, "❌ Error: No API key provided. Please enter one in your user settings."))
    else:
        client = openai.OpenAI(api_key=st.session_state.apikey)
        try:
            with st.spinner("Thinking..."):
                response_box = st.empty()
                collected = []
                stream = client.chat.completions.create(
                    model=st.session_state.model,
                    messages=[{"role": "user", "content": user_prompt}],
                    stream=True
                )
                for chunk in stream:
                    token = chunk.choices[0].delta.content or ""
                    collected.append(token)
                    response_box.markdown(f"**Mat-GPT (typing):** {''.join(collected)}")
                final = ''.join(collected)
                st.session_state.chat.append((user_prompt, final))
        except Exception as e:
            st.session_state.chat.append((user_prompt, f"❌ Error: {str(e)}"))
