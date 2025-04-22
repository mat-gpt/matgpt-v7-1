# db.py - Mat-GPT v7.0 Database Interface
import sqlite3
import pandas as pd

def init_db():
    conn = sqlite3.connect("matgpt.db")
    return conn

def get_memory_prompts(conn):
    try:
        df = pd.read_sql_query("SELECT * FROM assistant_prompts", conn)
        return df.to_dict(orient='records')
    except Exception:
        return []

def get_test_registry(conn):
    try:
        df = pd.read_sql_query("SELECT * FROM test_registry", conn)
        return df
    except Exception:
        return None