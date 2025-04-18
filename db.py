import sqlite3
import openai
import streamlit as st
import os

# Initialize OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", "")

# Default model selection
MODEL = "gpt-4o"

# Set up SQLite database connection
conn = sqlite3.connect(st.secrets["DATABASE_PATH"], check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id TEXT PRIMARY KEY,
            filename TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

def insert_file(id, filename):
    cursor.execute("INSERT INTO uploads (id, filename) VALUES (?, ?)", (id, filename))
    conn.commit()

def fetch_all_files():
    cursor.execute("SELECT * FROM uploads ORDER BY uploaded_at DESC")
    return cursor.fetchall()

def ask_openai(prompt, messages=[]):
    if not openai.api_key:
        return "❌ Error: No API key provided. Please enter one in your user settings."

    try:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=messages if messages else [{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except openai.OpenAIError as e:
        return f"❌ OpenAI API Error: {str(e)}"

    except Exception as e:
        return f"❌ Unexpected Error: {str(e)}"
