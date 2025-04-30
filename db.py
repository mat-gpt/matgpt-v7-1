# db.py – Mat-GPT v7.0 Database Interface

import sqlite3
import pandas as pd
import os

# Set consistent absolute path to matgpt.db regardless of Streamlit's working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_FILE = os.path.join(BASE_DIR, "matgpt.db")

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def get_connection():
    """Returns a live connection to the database with multi-thread safety."""
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    """Initializes database and creates required tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Table: assistant_prompts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assistant_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT
        )
    ''')

    # Table: test_registry (add column patch for date_created)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            profile TEXT
        )
    ''')
    try:
        cursor.execute('ALTER TABLE test_registry ADD COLUMN date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Table: file_tags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            session_id TEXT,
            test_name TEXT,
            tag_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Optional: Add more table initializations here as needed

    conn.commit()
    conn.close()

def get_memory_prompts():
    """Returns assistant prompts as a list of dicts."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM assistant_prompts", conn)
        return df.to_dict(orient='records')
    except Exception:
        return []
    finally:
        conn.close()

def get_test_registry():
    """Returns test registry records as a DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM test_registry ORDER BY date_created DESC", conn)
        return df
    except Exception:
        return None
    finally:
        conn.close()
