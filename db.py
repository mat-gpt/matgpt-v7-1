import sqlite3
import streamlit as st

# Connect using secret from Streamlit settings
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
