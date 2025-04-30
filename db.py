# db.py – Mat-GPT v7.0 Database Interface

import sqlite3
import pandas as pd
import os

# Set consistent absolute path to matgpt.db regardless of Streamlit's working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_FILE = os.path.join(BASE_DIR, "matgpt.db")

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
            profile TEXT,
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

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

    # ✅ Table: users (for login, API keys, roles)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            api_key TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ✅ Fix: Add missing sbd_protocol_schemas table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sbd_protocol_schemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            schema_json TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

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
