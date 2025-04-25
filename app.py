print("App is running!")
import sqlite3
import os

DB_PATH = "matgpt.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS assistant_prompts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        content TEXT
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS test_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_name TEXT,
        sender TEXT,
        receiver TEXT,
        profile TEXT,
        date TEXT,
        notes TEXT,
        source_file TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def insert_prompt(key, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO assistant_prompts (key, content) VALUES (?, ?)', (key, content))
    conn.commit()
    conn.close()

def fetch_prompts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT key, content FROM assistant_prompts')
    results = c.fetchall()
    conn.close()
    return {k: v for k, v in results}

def insert_test_record(test_name, sender, receiver, profile, date, notes, source_file):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    INSERT INTO test_registry (test_name, sender, receiver, profile, date, notes, source_file)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (test_name, sender, receiver, profile, date, notes, source_file))
    conn.commit()
    conn.close()

def fetch_all_tests():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM test_registry ORDER BY date DESC')
    results = c.fetchall()
    conn.close()
    return results
