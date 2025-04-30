import streamlit as st
import pandas as pd
import sqlite3
import os
import base64
import json
import time
import datetime

## Initialize database connection
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # ✅ Test Registry
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            profile TEXT,
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ✅ Users Table for Login System
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            role TEXT
        )
    ''')

    # ✅ Assistant Prompts Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS assistant_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT
        )
    ''')

    # ✅ sbd_protocol_schemas table (🔥 this was missing!)
    c.execute('''
        CREATE TABLE IF NOT EXISTS sbd_protocol_schemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            schema_json TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ✅ Seed default admin user if not present
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute('''
            INSERT INTO users (username, password, email, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin', 'admin@example.com', 'admin'))

    conn.commit()
    conn.close()

def load_memory():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT title, content FROM assistant_prompts")
    rows = c.fetchall()
    conn.close()
    memory = {}
    for title, content in rows:
        memory[title] = content
    return memory

memory_prompts = load_memory()

# --- LOGIN MANAGER ---

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    user = c.fetchone()
    conn.close()
    return user

def show_login_page():
    st.title("🔐 Mat-GPT Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state["user"] = {
                "id": user[0],
                "username": user[1],
                "role": user[4]
            }
            st.success(f"✅ Welcome back, {user[1]}!")
            st.experimental_rerun()
        else:
            st.error("❌ Invalid credentials")



# App Configuration
st.set_page_config(
    page_title="Mat-GPT v7.0",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Ensure database is initialized only once per session, after Streamlit fully loads
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state["db_initialized"] = True
if "user" not in st.session_state:
    show_login_page()
    st.stop()

# Sidebar Navigation
st.sidebar.title("🧠 Mat-GPT Modules")
page = st.sidebar.radio("Navigate", [
    "Home",
    "Upload",
    "Preview",
    "Chat",  # ✅ Add this line
    "Test Registry",
    "SBD Analyzer",
    "Memory Editor",
    "Session Browser",
    "Login / Users",
    "SkyDome (Coming Soon)",
    "Predictive (Coming Soon)"
])


# HOME PAGE
if page == "Home":
    st.title("Welcome to Mat-GPT v7.0")
    st.markdown("This is the official Mat-GPT v7.0 application — with memory, uploads, previews, test logging, and more.")
    st.info("To begin, choose a module from the left sidebar. Or just click around and pretend you know what you're doing. 😄")

    st.markdown("""
    ### 🤖 What Can I Do?
    - Upload CSV, PCAP, or SBD files
    - Chat through your rows like a data therapist
    - Decode SBD payloads (if schema is provided)
    - Analyze satellite visibility and latency trends
    - Track sessions and auto-tag everything (even your questionable file names)

    > “I’m not saying I’m smart… but I’ve definitely seen dumber code.” – Mat-GPT
    """)

    uploaded_file = st.file_uploader("Choose a CSV or PCAP file", type=["csv", "pcap"])

    if uploaded_file:
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"✅ File {uploaded_file.name} uploaded successfully to {UPLOAD_DIR}/")

# ==============================
# CHAT MODULE (Restored)
# ==============================
elif page == "Chat":
    st.title("💬 Chat with Mat-GPT")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            ("assistant", "Welcome to the Mat-GPT chat! I'm ready to help you analyze your data, decode logs, or rant about bad CSVs.")
        ]

    for role, message in st.session_state.chat_history:
        st.chat_message(role).markdown(message)

    user_input = st.chat_input("Ask Mat-GPT something...")

    if user_input:
        st.chat_message("user").markdown(user_input)
        st.session_state.chat_history.append(("user", user_input))

        # STUBBED RESPONSE – works without OpenAI key
        response = f"🤖 Mat-GPT says: '{user_input}' (replace this with real model output)"
        st.chat_message("assistant").markdown(response)
        st.session_state.chat_history.append(("assistant", response))

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.chat_input("Ask Mat-GPT something...")
    if user_input:
        st.session_state.chat_history.append(("user", user_input))
        # Replace this with actual OpenAI call
        response = f"🤖 Mat-GPT (stub): You said — '{user_input}'"
        st.session_state.chat_history.append(("assistant", response))

    for role, message in st.session_state.chat_history:
        st.chat_message(role).markdown(message)


# PREVIEW PAGE
elif page == "Preview":
    st.title("🧾 Preview Uploaded Files")
    uploaded_files = os.listdir(UPLOAD_DIR)

    if uploaded_files:
        selected_file = st.selectbox("Select a file to preview", uploaded_files)
        file_path = os.path.join(UPLOAD_DIR, selected_file)

        if selected_file.endswith(".csv"):
            try:
                df = pd.read_csv(file_path)
                st.success(f"Loaded {len(df)} rows from {selected_file}")

                # Filter + Chat Preview
                columns = df.columns.tolist()
                selected_columns = st.multiselect("Select columns to include", columns, default=columns)

                if selected_columns:
                    filtered_df = df[selected_columns]

                    row_limit = st.slider("Rows to preview", 10, 1000, 50)
                    start_index = st.number_input("Start from row", 0, len(filtered_df) - 1, 0)

                    st.markdown(f"Streaming **{row_limit}** rows from index **{start_index}** with columns: {', '.join(selected_columns)}")

                    for idx in range(start_index, min(start_index + row_limit, len(filtered_df))):
                        row = filtered_df.iloc[idx]
                        row_dict = row.to_dict()
                        formatted_row = "\n".join([f"**{k}**: {v}" for k, v in row_dict.items()])

                        st.chat_message("user").markdown(f"Here’s the next row previewed:\n\n{formatted_row}")
                        st.chat_message("assistant").markdown(
                            f"🤖 *(Assistant)*: Interesting! Looks like row {idx} contains some juicy details... 🕵️\n"
                            f"Let's keep going — data never sleeps!"
                        )
                        time.sleep(0.01)

                else:
                    st.warning("Select at least one column to preview.")

            except Exception as e:
                st.error(f"❌ Failed to preview file: {e}")

        elif selected_file.endswith(".pcap"):
            st.info("PCAP preview not yet supported — decoder coming soon.")
        else:
            st.warning("Unknown file format. Cannot preview.")
    else:
        st.warning("No files found in upload directory.")
elif page == "Test Registry":
    st.title("🧪 Test Registry")
    conn = get_connection()
    c = conn.cursor()

    st.subheader("Register New Test")

    with st.form("test_registry_form"):
        sender = st.text_input("Sender Device")
        receiver = st.text_input("Receiver Device")
        profile = st.text_input("Profile Name")

        submitted = st.form_submit_button("Submit Entry")
        if submitted:
            if sender and receiver:
                c.execute('''
                    INSERT INTO test_registry (sender, receiver, profile)
                    VALUES (?, ?, ?)
                ''', (sender, receiver, profile or "None"))
                conn.commit()
                st.success("✅ Test logged.")
            else:
                st.error("Sender and Receiver fields are required.")

    st.divider()
    st.subheader("Registered Tests")

    c.execute("SELECT * FROM test_registry ORDER BY date_created DESC")
    rows = c.fetchall()

    if rows:
        for row in rows:
            st.write(f"📄 ID: {row[0]} | Sender: {row[1]} | Receiver: {row[2]} | Profile: {row[3]} | Date: {row[4]}")
    else:
        st.info("No test records found.")

    conn.close()
# SBD ANALYZER PAGE
elif page == "SBD Analyzer":
    st.title("🛰️ SBD Analyzer (Prototype)")

    sbd_file = st.file_uploader("Upload an SBD binary file", type=["sbd"])

    if sbd_file:
        sbd_path = os.path.join(UPLOAD_DIR, sbd_file.name)
        with open(sbd_path, "wb") as f:
            f.write(sbd_file.getbuffer())
        st.success(f"SBD file {sbd_file.name} uploaded.")

        st.info("SBD decoding logic not yet implemented — feature coming in v7.1.")

# SKYDOME PAGE (Placeholder)
elif page == "SkyDome (Coming Soon)":
    st.title("🌐 SkyDome Analyzer")
    st.info("SkyDome visibility grading and overlay tools coming in Mat-GPT v7.2.")

# PREDICTIVE PAGE (Placeholder)
elif page == "Predictive (Coming Soon)":
    st.title("📊 Predictive Modeling")
    st.info("Predictive modeling and test behavior forecasting will be part of Mat-GPT v7.4.")
    st.divider()
    st.subheader("SBD File Details")

    if 'sbd_file' in locals() and sbd_file:
        raw_bytes = sbd_file.getvalue()
        sbd_path = os.path.join(UPLOAD_DIR, sbd_file.name)

        file_info = {
            "Filename": sbd_file.name,
            "Size (bytes)": len(raw_bytes),
            "Saved Path": sbd_path,
            "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.json(file_info)

        st.subheader("Raw Hex Dump")
        hex_dump = ' '.join(f'{b:02X}' for b in raw_bytes[:256])
        st.code(hex_dump, language="bash")

        st.subheader("Payload Decoder (coming soon)")
        st.info("Automatic protocol decoding will be available when schema is provided.")

        # Store basic info in DB (future registry)
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS sbd_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                path TEXT,
                size INTEGER,
                timestamp TEXT
            )
        ''')
        c.execute('''
            INSERT INTO sbd_files (filename, path, size, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (
            sbd_file.name,
            sbd_path,
            len(raw_bytes),
            datetime.datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        st.success("✅ File info saved to registry.")
    else:
        st.warning("⚠️ No SBD file uploaded yet.")

# ==============================
# SBD Analyzer Continued - Real Expansion
# ==============================

# Expanded SBD File Processing

import struct

# Section: Schema Upload
st.divider()
st.subheader("Optional: Upload Protocol Schema (JSON)")

schema_file = st.file_uploader("Upload a JSON protocol schema", type=["json"], key="schema")

protocol_schema = None
if schema_file:
    try:
        protocol_schema = json.load(schema_file)
        st.success(f"✅ Schema {schema_file.name} loaded successfully.")
    except Exception as e:
        st.error(f"❌ Failed to parse schema: {e}")

# Section: Decode Attempt
if protocol_schema and sbd_file:
    st.divider()
    st.subheader("SBD Decoding Preview")

    raw_bytes = sbd_file.getvalue()
    hex_stream = ''.join(f'{b:02X}' for b in raw_bytes)
    st.code(hex_stream[:500] + ("..." if len(hex_stream) > 500 else ""), language="bash")

    # Assume schema has field list
    fields = protocol_schema.get("fields", [])

    if fields:
        try:
            decoded_output = {}
            cursor = 0
            for field in fields:
                field_name = field.get("name", "Unnamed")
                field_type = field.get("type", "uint8")
                field_length = field.get("length", 1)

                if field_type == "uint8":
                    val = raw_bytes[cursor]
                    decoded_output[field_name] = val
                    cursor += 1

                elif field_type == "uint16":
                    val = int.from_bytes(raw_bytes[cursor:cursor+2], "big")
                    decoded_output[field_name] = val
                    cursor += 2

                elif field_type == "uint32":
                    val = int.from_bytes(raw_bytes[cursor:cursor+4], "big")
                    decoded_output[field_name] = val
                    cursor += 4

                elif field_type == "bytes":
                    val = raw_bytes[cursor:cursor+field_length]
                    decoded_output[field_name] = base64.b64encode(val).decode()
                    cursor += field_length

                else:
                    decoded_output[field_name] = "Unknown Type"

            st.success("✅ SBD decoded based on uploaded schema:")
            st.json(decoded_output)

            # Future: Save decoded payload into DB
        except Exception as decode_error:
            st.error(f"❌ Decoding failed: {decode_error}")

    else:
        st.warning("⚠️ No fields defined in uploaded schema.")

# Section: If No Schema Uploaded
if 'sbd_file' in locals() and sbd_file and not protocol_schema:
    st.info("Upload a protocol schema to decode payload.")


# New Table for Decoded Data (future extension)
def create_decoded_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS decoded_sbd_payloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            decoded_json TEXT,
            FOREIGN KEY(file_id) REFERENCES sbd_files(id)
        )
    ''')
    conn.commit()
    conn.close()

create_decoded_table()

# Helper Functions (Real)
def insert_decoded_payload(file_id, decoded_json):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO decoded_sbd_payloads (file_id, decoded_json)
        VALUES (?, ?)
    ''', (file_id, json.dumps(decoded_json)))
    conn.commit()
    conn.close()

# Placeholder Future Hook
def match_protocol_schema(uploaded_schema):
    if not uploaded_schema:
        return "Unknown"
    # Future expansion: match by device type
    return "Generic Device"

# Section: Future Enhancements Notes
st.divider()
st.subheader("Coming Enhancements")
st.markdown("""
- 🔜 Auto-match SBD payloads with internal known schemas
- 🔜 Decode common message formats
- 🔜 Save decoded results into registry for search/query
- 🔜 Show decoding confidence scores
- 🔜 Download decoded output as JSON
""")

# System: Database Table Setup if needed
def initialize_registry_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sbd_protocol_schemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            schema_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

initialize_registry_tables()

# Upload Protocol Schema to Local DB
st.divider()
st.subheader("Save Protocol Schema (Manual Upload)")

if protocol_schema:
    save_name = st.text_input("Schema Save Name")
    if st.button("Save Schema"):
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO sbd_protocol_schemas (name, schema_json)
            VALUES (?, ?)
        ''', (save_name or f"Unnamed-{datetime.datetime.now().isoformat()}", json.dumps(protocol_schema)))
        conn.commit()
        conn.close()
        st.success(f"✅ Schema saved as {save_name}")

# Section: List Saved Schemas
st.divider()
st.subheader("Registered Protocol Schemas")

# Reload protocol schema registry from DB (SBD Analyzer context)
conn = get_connection()
c = conn.cursor()
c.execute('SELECT id, name, timestamp FROM sbd_protocol_schemas ORDER BY timestamp DESC')
schemas = c.fetchall()
conn.close()

if schemas:
    for schema in schemas:
        st.markdown(f"📜 **{schema[1]}** (ID: {schema[0]}) — Saved: {schema[2]}")
else:
    st.info("⚠️ No protocol schemas saved yet.")


# ==============================
# End of SBD Analyzer Expansion (Real)
# ==============================
# ==============================
# Session Tracking and Predictive Modeling
# ==============================

import uuid
import random
from sklearn.linear_model import LinearRegression
import numpy as np

# Session State Setup
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = str(uuid.uuid4())

session_id = st.session_state['session_id']

# Create Table for Sessions
def create_session_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

create_session_table()

# Save Current Session
def save_session(session_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO sessions (id) VALUES (?)
    ''', (session_id,))
    conn.commit()
    conn.close()

save_session(session_id)

# Add Predictive Modeling Base
if page == "Predictive (Coming Soon)":
    st.title("📈 Predictive Modeling Dashboard")

    st.info(f"Session ID: {session_id}")

    st.subheader("Select a Device Profile")
    device_profiles = ["SkyLink C100", "MissionLink 700", "Velaris UAV", "PSTN Baseline"]
    selected_profile = st.selectbox("Choose a profile:", device_profiles)

    st.subheader("Upload Training Data (CSV)")

    training_file = st.file_uploader("Upload Training CSV", type=["csv"], key="training_data")

    model = None
    prediction_ready = False

    if training_file:
        try:
            training_df = pd.read_csv(training_file)
            st.success(f"✅ Loaded {len(training_df)} rows.")

            # Display sample
            st.dataframe(training_df.head())

            if 'latency' in training_df.columns and 'timestamp' in training_df.columns:
                X = np.array(range(len(training_df))).reshape(-1, 1)
                y = training_df['latency'].values

                model = LinearRegression()
                model.fit(X, y)

                st.success("✅ Basic latency trend model trained.")
                prediction_ready = True
            else:
                st.error("❌ CSV must include 'timestamp' and 'latency' columns.")
        except Exception as train_error:
            st.error(f"❌ Failed to load training data: {train_error}")

    st.divider()
    st.subheader("Predict Future Behavior")

    if prediction_ready:
        future_steps = st.slider("How many future points to predict?", 5, 100, 10)
        future_X = np.array(range(len(training_df), len(training_df)+future_steps)).reshape(-1, 1)
        future_predictions = model.predict(future_X)

        prediction_df = pd.DataFrame({
            'Future Index': range(len(training_df), len(training_df)+future_steps),
            'Predicted Latency': future_predictions
        })

        st.line_chart(prediction_df.set_index('Future Index'))

        st.success("✅ Prediction plotted.")

    else:
        st.info("Upload valid training data to enable prediction.")

# Helper for Future Predictive Expansion
def generate_dummy_latency_profile(device_name):
    if "SkyLink" in device_name:
        return [random.uniform(450, 600) for _ in range(50)]
    elif "MissionLink" in device_name:
        return [random.uniform(600, 750) for _ in range(50)]
    elif "Velaris" in device_name:
        return [random.uniform(1000, 1400) for _ in range(50)]
    else:
        return [random.uniform(200, 400) for _ in range(50)]

# ==============================
# End of Session + Predictive Expansion
# ==============================
# ==============================
# SkyDome Analyzer Expansion (Photo Upload + Registry)
# ==============================

# Create SkyDome Tables if Needed
def create_skydome_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS skydome_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            view_direction TEXT,
            filename TEXT,
            path TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

create_skydome_tables()

# SkyDome Analyzer Active
if page == "SkyDome (Coming Soon)":
    st.title("🌐 SkyDome Analyzer - Photo Capture")

    st.markdown("""
        Upload directional installation photos for SkyDome visibility mapping.
        
        **Recommended views:** North, East, South, West.
    """)

    photo_directions = ["North", "East", "South", "West"]

    uploaded_photos = {}
    for direction in photo_directions:
        uploaded_photos[direction] = st.file_uploader(f"Upload {direction} Facing Photo", type=["jpg", "jpeg", "png"], key=f"photo_{direction}")

    # Save Photos and Register
    if st.button("Save Uploaded Photos"):
        saved = False
        for direction, file_obj in uploaded_photos.items():
            if file_obj:
                save_path = os.path.join(UPLOAD_DIR, f"{direction}_{file_obj.name}")
                with open(save_path, "wb") as f:
                    f.write(file_obj.getbuffer())

                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO skydome_photos (view_direction, filename, path)
                    VALUES (?, ?, ?)
                ''', (direction, file_obj.name, save_path))
                conn.commit()
                conn.close()

                st.success(f"✅ Saved {direction} photo: {file_obj.name}")
                saved = True

        if not saved:
            st.warning("⚠️ No photos were uploaded to save.")

    st.divider()
    st.subheader("Previously Uploaded Photos")

    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, view_direction, filename, upload_time FROM skydome_photos ORDER BY upload_time DESC')
    previous_photos = c.fetchall()
    conn.close()

    if previous_photos:
        for photo in previous_photos:
            st.write(f"🖼️ {photo[1]} View | File: {photo[2]} | Uploaded: {photo[3]}")
    else:
        st.info("No photos uploaded yet. Begin your SkyDome mapping now!")

# ==============================
# End of SkyDome Expansion (Photo Upload + Registry)
# ==============================
# ==============================
# SkyDome Analyzer Expansion - Part 2 (Visibility Grading + Metadata)
# ==============================

# Create additional SkyDome Tables if Needed
def create_skydome_visibility_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS skydome_visibility (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            view_direction TEXT,
            azimuth_start INTEGER,
            azimuth_end INTEGER,
            elevation_min INTEGER,
            elevation_max INTEGER,
            visibility_grade TEXT,
            notes TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

create_skydome_visibility_table()

# Active SkyDome Visibility Input Page
if page == "SkyDome (Coming Soon)":
    st.title("🌐 SkyDome Analyzer - Visibility Grading")

    st.markdown("""
    Record azimuth/elevation metadata and assign visibility grades (A–F scale) for each view.
    
    - **A = Completely Clear**
    - **F = Completely Blocked**
    """)

    st.divider()
    st.subheader("Submit Visibility Grades")

    with st.form("visibility_grading_form"):
        selected_direction = st.selectbox("Select View Direction", ["North", "East", "South", "West"])
        az_start = st.slider("Azimuth Start (°)", 0, 360, 0)
        az_end = st.slider("Azimuth End (°)", 0, 360, 90)
        el_min = st.slider("Minimum Elevation (°)", 0, 90, 5)
        el_max = st.slider("Maximum Elevation (°)", 0, 90, 90)
        grade = st.selectbox("Visibility Grade", ["A", "B", "C", "D", "E", "F"])
        notes = st.text_area("Additional Notes (Optional)", "")

        submit_visibility = st.form_submit_button("Save Visibility Entry")

        if submit_visibility:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO skydome_visibility (
                    view_direction, azimuth_start, azimuth_end,
                    elevation_min, elevation_max, visibility_grade, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (selected_direction, az_start, az_end, el_min, el_max, grade, notes))
            conn.commit()
            conn.close()

            st.success(f"✅ Visibility entry for {selected_direction} saved.")

    st.divider()
    st.subheader("Saved Visibility Entries")

    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT view_direction, azimuth_start, azimuth_end, elevation_min, elevation_max, visibility_grade, notes, timestamp FROM skydome_visibility ORDER BY timestamp DESC')
    visibility_entries = c.fetchall()
    conn.close()

    if visibility_entries:
        for entry in visibility_entries:
            st.markdown(f"""
            - 📍 **{entry[0]}** View
            - Azimuth Range: **{entry[1]}° to {entry[2]}°**
            - Elevation Range: **{entry[3]}° to {entry[4]}°**
            - Visibility Grade: **{entry[5]}**
            - Notes: {entry[6]}
            - Timestamp: {entry[7]}
            """)
            st.divider()
    else:
        st.info("No visibility entries logged yet. Start grading your views!")

# ==============================
# End of SkyDome Analyzer Expansion - Part 2
# ==============================
# ==============================
# SkyDome Analyzer - Visibility Grading Expansion
# ==============================

# Extend SkyDome Table if Needed
def extend_skydome_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        ALTER TABLE skydome_photos
        ADD COLUMN azimuth INTEGER
    ''')
    c.execute('''
        ALTER TABLE skydome_photos
        ADD COLUMN elevation INTEGER
    ''')
    c.execute('''
        ALTER TABLE skydome_photos
        ADD COLUMN visibility_grade TEXT
    ''')
    conn.commit()
    conn.close()

# Try extension, ignore if already done
try:
    extend_skydome_table()
except:
    pass

# SkyDome Visibility Grading Form
if page == "SkyDome (Coming Soon)":
    st.title("🌐 SkyDome Analyzer - Visibility Grading")

    st.markdown("""
        Assign azimuth, elevation, and visibility grades (A–F) to uploaded photos.
        
        **Grades:**
        - A = Perfect Sky
        - B = Minor Obstruction
        - C = Moderate Obstruction
        - D = Heavy Obstruction
        - E = Nearly Blocked
        - F = Fully Blocked
    """)

    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, view_direction, filename FROM skydome_photos ORDER BY upload_time DESC')
    photo_entries = c.fetchall()
    conn.close()

    if photo_entries:
        for entry in photo_entries:
            photo_id, direction, filename = entry

            st.divider()
            st.subheader(f"🖼️ {direction} View – {filename}")

            with st.form(f"grading_form_{photo_id}"):
                azimuth = st.slider(f"Azimuth for {direction}", 0, 360, 0, key=f"az_{photo_id}")
                elevation = st.slider(f"Elevation for {direction}", 0, 90, 0, key=f"el_{photo_id}")
                visibility_grade = st.selectbox(
                    f"Visibility Grade for {direction}",
                    ["A", "B", "C", "D", "E", "F"],
                    key=f"grade_{photo_id}"
                )

                submit = st.form_submit_button("Save Visibility Grade")

                if submit:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute('''
                        UPDATE skydome_photos
                        SET azimuth = ?, elevation = ?, visibility_grade = ?
                        WHERE id = ?
                    ''', (azimuth, elevation, visibility_grade, photo_id))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Saved visibility data for {direction} view!")

    else:
        st.info("No photos uploaded yet. Please upload photos first.")

# View Graded Results (Summary Section)
    st.divider()
    st.subheader("Graded SkyDome Views Summary")

    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT view_direction, azimuth, elevation, visibility_grade FROM skydome_photos WHERE visibility_grade IS NOT NULL')
    graded_views = c.fetchall()
    conn.close()

    if graded_views:
        for view in graded_views:
            st.write(f"🌎 {view[0]} | Azimuth: {view[1]}° | Elevation: {view[2]}° | Grade: {view[3]}")
    else:
        st.info("No visibility grading submitted yet.")

# ==============================
# End of SkyDome Analyzer - Visibility Grading Expansion
# ==============================
# ==============================
# SkyDome Analyzer - Radar Chart Visualization
# ==============================

import matplotlib.pyplot as plt

# Mapping grade letters to numeric scores (A = 5, F = 0)
grade_to_score = {
    "A": 5,
    "B": 4,
    "C": 3,
    "D": 2,
    "E": 1,
    "F": 0
}

# SkyDome Radar Chart Display
if page == "SkyDome (Coming Soon)":
    st.title("🌐 SkyDome Analyzer - Radar Chart")

    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT view_direction, visibility_grade FROM skydome_photos WHERE visibility_grade IS NOT NULL')
    graded_data = c.fetchall()
    conn.close()

    if graded_data:
        st.subheader("Radar Chart of Visibility Grades")

        directions = []
        scores = []

        for direction, grade in graded_data:
            if grade in grade_to_score:
                directions.append(direction)
                scores.append(grade_to_score[grade])

        if directions and scores:
            # Radar requires circular duplication
            directions.append(directions[0])
            scores.append(scores[0])

            angles = [n / float(len(directions)) * 2 * 3.14159265 for n in range(len(directions))]

            fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))
            ax.set_theta_offset(3.14159265 / 2)
            ax.set_theta_direction(-1)

            plt.xticks(angles[:-1], directions[:-1])

            ax.plot(angles, scores, linewidth=2, linestyle='solid')
            ax.fill(angles, scores, alpha=0.25)

            st.pyplot(fig)

        else:
            st.info("No valid graded directions to plot.")
    else:
        st.info("No graded SkyDome views yet.")

# ==============================
# End of SkyDome Analyzer - Radar Chart Visualization
# ==============================
# ==============================
# Predictive Modeling - Training Stats + Enhanced Plot
# ==============================

from sklearn.metrics import mean_squared_error

# Enhanced Predictive Modeling Page
if page == "Predictive (Coming Soon)":
    st.title("📈 Predictive Modeling Dashboard (Expanded)")

    st.info(f"Session ID: {session_id}")

    st.subheader("Select a Device Profile")
    device_profiles = ["SkyLink C100", "MissionLink 700", "Velaris UAV", "PSTN Baseline"]
    selected_profile = st.selectbox("Choose a profile:", device_profiles, key="profile_select")

    st.subheader("Upload Training Data (CSV)")

    training_file = st.file_uploader("Upload Training CSV for Model Training", type=["csv"], key="predictive_training")

    model = None
    prediction_ready = False
    training_df = None

    if training_file:
        try:
            training_df = pd.read_csv(training_file)
            st.success(f"✅ Loaded {len(training_df)} rows.")

            st.dataframe(training_df.head())

            if 'timestamp' in training_df.columns and 'latency' in training_df.columns:
                # Prepare data
                X = np.array(range(len(training_df))).reshape(-1, 1)
                y = training_df['latency'].values

                model = LinearRegression()
                model.fit(X, y)

                # Model Stats
                y_pred = model.predict(X)
                mse = mean_squared_error(y, y_pred)
                trend_slope = model.coef_[0]

                st.success(f"✅ Model Trained - MSE: {mse:.2f}, Slope: {trend_slope:.4f}")

                # Original Latency vs Predicted
                st.subheader("Latency vs Time (Original vs Predicted)")

                latency_plot_df = pd.DataFrame({
                    'Timestamp': range(len(training_df)),
                    'Actual Latency': y,
                    'Predicted Latency': y_pred
                })

                st.line_chart(latency_plot_df.set_index('Timestamp'))

                prediction_ready = True

            else:
                st.error("❌ CSV must include at least 'timestamp' and 'latency' columns.")
        except Exception as train_error:
            st.error(f"❌ Failed to load or process training data: {train_error}")

    st.divider()

    # Predict Future Behavior
    if prediction_ready:
        st.subheader("Predict Future Behavior")

        future_steps = st.slider("How many future points to predict?", 5, 100, 10, key="future_steps_predictive")
        future_X = np.array(range(len(training_df), len(training_df)+future_steps)).reshape(-1, 1)
        future_predictions = model.predict(future_X)

        prediction_df = pd.DataFrame({
            'Future Index': range(len(training_df), len(training_df)+future_steps),
            'Predicted Latency': future_predictions
        })

        st.line_chart(prediction_df.set_index('Future Index'))

        st.success("✅ Future latency prediction complete.")

    else:
        st.info("Upload and train with a valid CSV to enable predictions.")

# ==============================
# End of Predictive Modeling - Training Stats + Enhanced Plot
# ==============================
# ==============================
# SkyDome Composite Overlay Viewer
# ==============================

# SkyDome Composite Page
if page == "SkyDome (Coming Soon)":
    st.title("🌐 SkyDome Analyzer - Composite Overlay")

    st.markdown("""
        View and manage multiple directional SkyDome installation photos together.

        **Use case:**
        - Compare North/East/South/West photos side-by-side
        - Evaluate obstruction levels visually
    """)

    st.divider()
    st.subheader("Uploaded Photos")

    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT view_direction, filename, path FROM skydome_photos ORDER BY view_direction ASC')
    all_photos = c.fetchall()
    conn.close()

    if all_photos:
        photo_cols = st.columns(2)

        for idx, photo in enumerate(all_photos):
            view_direction, filename, path = photo

            if os.path.exists(path):
                with open(path, "rb") as img_file:
                    img_bytes = img_file.read()
                    b64_img = base64.b64encode(img_bytes).decode()

                img_html = f'<img src="data:image/jpeg;base64,{b64_img}" width="100%" style="border:1px solid #ccc; border-radius:8px; margin-bottom:10px;"/>'

                with photo_cols[idx % 2]:
                    st.markdown(f"**{view_direction} View**")
                    st.markdown(img_html, unsafe_allow_html=True)
                    st.caption(f"📂 {filename}")
            else:
                st.warning(f"⚠️ Missing file: {filename}")

    else:
        st.info("No installation photos uploaded yet.")

    st.divider()

    # Bulk Photo Management Section
    st.subheader("Manage Uploaded Photos")

    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, view_direction, filename FROM skydome_photos ORDER BY upload_time DESC')
    photo_list = c.fetchall()
    conn.close()

    if photo_list:
        selected_to_delete = st.multiselect(
            "Select photos to delete:",
            [f"{photo[1]} - {photo[2]}" for photo in photo_list]
        )

        if st.button("Delete Selected Photos"):
            deleted = False
            for selected_entry in selected_to_delete:
                for photo in photo_list:
                    db_id, direction, filename = photo
                    if selected_entry == f"{direction} - {filename}":
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute('DELETE FROM skydome_photos WHERE id = ?', (db_id,))
                        conn.commit()
                        conn.close()

                        try:
                            os.remove(os.path.join(UPLOAD_DIR, filename))
                        except Exception:
                            pass  # Ignore if already deleted

                        deleted = True

            if deleted:
                st.success("✅ Selected photos deleted.")
            else:
                st.warning("⚠️ No matching photos found to delete.")

    else:
        st.info("No photos available for deletion.")

# ==============================
# End of SkyDome Composite Overlay Viewer
# ==============================
# ==============================
# Assistant Memory Editor - Prompt Management Tool
# ==============================

if page == "Memory Editor":
    st.title("🧠 Assistant Prompt Memory Editor")

    st.markdown("""
    Manage internal assistant memory prompts stored in the assistant_prompts database table.

    These prompts are loaded at app startup and influence system behavior across all modules.
    """)

    # View existing prompts
    st.subheader("Stored Prompts")

    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, title, content FROM assistant_prompts ORDER BY id ASC')
    prompts = c.fetchall()

    if prompts:
        for prompt in prompts:
            st.markdown(f"**🧾 {prompt[1]}**")
            st.code(prompt[2], language="markdown")
            with st.expander("Edit Prompt"):
                new_title = st.text_input("Title", value=prompt[1], key=f"title_{prompt[0]}")
                new_content = st.text_area("Content", value=prompt[2], height=150, key=f"content_{prompt[0]}")
                if st.button("Update", key=f"update_{prompt[0]}"):
                    c.execute('''
                        UPDATE assistant_prompts
                        SET title = ?, content = ?
                        WHERE id = ?
                    ''', (new_title, new_content, prompt[0]))
                    conn.commit()
                    st.success(f"✅ Prompt {new_title} updated.")
    else:
        st.info("No assistant prompts found.")

    st.divider()
    st.subheader("➕ Add New Prompt")

    with st.form("add_prompt_form"):
        new_title = st.text_input("New Prompt Title")
        new_content = st.text_area("New Prompt Content", height=150)
        submitted = st.form_submit_button("Add Prompt")

        if submitted:
            if new_title and new_content:
                c.execute('''
                    INSERT INTO assistant_prompts (title, content)
                    VALUES (?, ?)
                ''', (new_title, new_content))
                conn.commit()
                st.success(f"✅ Prompt {new_title} added.")
            else:
                st.error("Both title and content are required.")

    conn.close()

# ==============================
# End of Assistant Memory Editor
# ==============================
# ==============================
# Session Browser + File Tagging Tool
# ==============================

if page == "Memory Editor":  # ⬅ Extend the sidebar first if not done already
    pass  # Already handled above

elif page == "Session Browser":
    st.title("🧾 Session Browser + File Tagger")

    # List known sessions
    st.subheader("📚 Known Sessions")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, start_time FROM sessions ORDER BY start_time DESC")
    sessions = c.fetchall()
    conn.close()

    if sessions:
        for sid, ts in sessions:
            st.write(f"🧠 {sid} | Started: {ts}")
    else:
        st.info("No sessions found.")

    st.divider()
    st.subheader("📌 Tag Uploaded File with Metadata")

    uploaded_files = os.listdir(UPLOAD_DIR)
    if not uploaded_files:
        st.warning("No uploaded files found in uploads/ directory.")
    else:
        with st.form("tag_file_form"):
            selected_file = st.selectbox("Select File to Tag", uploaded_files)
            tag_session_id = st.text_input("Session ID (auto-filled)", value=session_id)
            tag_test_name = st.text_input("Test Name / Purpose")
            tag_type = st.selectbox("File Type", ["CSV", "PCAP", "SBD", "Schema", "Other"])

            submit_tag = st.form_submit_button("Tag File")

            if submit_tag and selected_file and tag_test_name:
                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    CREATE TABLE IF NOT EXISTS file_tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT,
                        session_id TEXT,
                        test_name TEXT,
                        tag_type TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                c.execute('''
                    INSERT INTO file_tags (filename, session_id, test_name, tag_type)
                    VALUES (?, ?, ?, ?)
                ''', (selected_file, tag_session_id, tag_test_name, tag_type))
                conn.commit()
                conn.close()

                st.success(f"✅ Tagged {selected_file} as {tag_type} under session {tag_session_id}")

    st.divider()
    st.subheader("📂 Tagged File Registry")

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT filename, session_id, test_name, tag_type, timestamp FROM file_tags ORDER BY timestamp DESC")
    tagged_files = c.fetchall()
    conn.close()

    if tagged_files:
        for f in tagged_files:
            st.write(f"📁 {f[0]} | Session: {f[1]} | Test: {f[2]} | Type: {f[3]} | Time: {f[4]}")
    else:
        st.info("No file tags recorded yet.")
# ==============================
# Part 12: Auto-Tagging Framework + Upload Hook
# ==============================

import re

# Create AutoTag Table if needed
def create_autotag_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS auto_tag_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT,
            tag_type TEXT,
            sender TEXT,
            receiver TEXT,
            profile TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_autotag_table()

# Hook: Auto-Tag Files on Upload (invoked in Upload module)
def auto_tag_file(filename):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM auto_tag_rules")
    rules = c.fetchall()

    matched_tags = []

    for rule in rules:
        pattern = rule[1]
        if re.search(pattern, filename):
            matched_tags.append({
                "tag_type": rule[2],
                "sender": rule[3],
                "receiver": rule[4],
                "profile": rule[5],
                "notes": rule[6]
            })

    conn.close()
    return matched_tags

# Apply Auto-Tagging Logic in Upload Section (inject here if not already done)
def apply_auto_tagging_on_upload(uploaded_file):
    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success(f"✅ File {uploaded_file.name} uploaded successfully to {UPLOAD_DIR}/")

    auto_tags = auto_tag_file(uploaded_file.name)

    if auto_tags:
        st.info("🔎 Auto-Tagging Match Found:")
        for tag in auto_tags:
            st.write(f"📌 Type: {tag['tag_type']} | Sender: {tag['sender']} | Receiver: {tag['receiver']} | Profile: {tag['profile']}")
            
            conn = get_connection()
            c = conn.cursor()

            # Register file tag
            c.execute('''
                CREATE TABLE IF NOT EXISTS file_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    session_id TEXT,
                    test_name TEXT,
                    tag_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            c.execute('''
                INSERT INTO file_tags (filename, session_id, test_name, tag_type)
                VALUES (?, ?, ?, ?)
            ''', (uploaded_file.name, st.session_state.get("session_id", "N/A"), tag['notes'] or "Auto", tag['tag_type']))

            # Register test entry
            c.execute('''
                INSERT INTO test_registry (sender, receiver, profile)
                VALUES (?, ?, ?)
            ''', (tag['sender'], tag['receiver'], tag['profile'] or "None"))

            conn.commit()
            conn.close()

        st.success("✅ Auto-tag applied and registered.")
    else:
        st.warning("⚠️ No auto-tag rules matched this filename.")

# Replace existing upload write logic in "Upload" section with this:
# apply_auto_tagging_on_upload(uploaded_file)

# ==============================
# Auto-Tag Rule Editor Page (Optional UI Admin)
# ==============================

if page == "Memory Editor":  # Append to admin area if needed
    st.divider()
    st.subheader("🧠 Auto-Tagging Rules")

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, pattern, tag_type, sender, receiver, profile, notes FROM auto_tag_rules ORDER BY id ASC")
    rules = c.fetchall()

    if rules:
        for r in rules:
            st.markdown(f"**📐 Pattern:** {r[1]}")
            st.markdown(f"- Type: {r[2]} | Sender: {r[3]} | Receiver: {r[4]} | Profile: {r[5]} | Notes: {r[6]}")
    else:
        st.info("No auto-tag rules configured yet.")

    st.divider()
    st.subheader("➕ Add New Auto-Tag Rule")
    with st.form("add_autotag_rule"):
        new_pattern = st.text_input("Regex Pattern (matches filename)")
        new_type = st.selectbox("Tag Type", ["CSV", "SBD", "Schema", "PCAP", "Other"])
        new_sender = st.text_input("Sender Device")
        new_receiver = st.text_input("Receiver Device")
        new_profile = st.text_input("Profile Name")
        new_notes = st.text_area("Notes / Test Name")
        submit_rule = st.form_submit_button("Add Rule")

        if submit_rule and new_pattern:
            c = conn.cursor()
            c.execute('''
                INSERT INTO auto_tag_rules (pattern, tag_type, sender, receiver, profile, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (new_pattern, new_type, new_sender, new_receiver, new_profile, new_notes))
            conn.commit()
            st.success("✅ Rule added.")

    conn.close()

# ==============================
# End of Part 12 – Auto-Tagging Framework
# ==============================
# ==============================
# Part 14: CSV Column Tagger + Auto Schema Extractor
# ==============================

# Create table for column tagging if not already exists
def create_column_schema_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS csv_column_schemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            column_name TEXT,
            semantic_tag TEXT,
            session_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

create_column_schema_table()

# UI for tagging columns
if page == "Preview":
    st.title("🧾 Preview Uploaded Files + Schema Tagger")
    uploaded_files = os.listdir(UPLOAD_DIR)

    if uploaded_files:
        selected_file = st.selectbox("Select a file to preview", uploaded_files)
        file_path = os.path.join(UPLOAD_DIR, selected_file)

        if selected_file.endswith(".csv"):
            try:
                df = pd.read_csv(file_path)
                st.success(f"Loaded {len(df)} rows from {selected_file}")

                columns = df.columns.tolist()

                st.subheader("🧩 Column Semantic Tagger")

                tag_options = ["timestamp", "latency", "packet_id", "size", "iteration", "device", "custom"]
                schema_entries = []

                for col in columns:
                    with st.expander(f"🧱 Column: {col}"):
                        tag = st.selectbox(f"Tag for {col}", tag_options, key=f"tag_{col}")
                        if tag == "custom":
                            tag = st.text_input(f"Enter custom tag for {col}", key=f"custom_{col}")
                        schema_entries.append((col, tag))

                if st.button("💾 Save Schema Tags"):
                    conn = get_connection()
                    c = conn.cursor()
                    for col_name, semantic_tag in schema_entries:
                        c.execute('''
                            INSERT INTO csv_column_schemas (filename, column_name, semantic_tag, session_id)
                            VALUES (?, ?, ?, ?)
                        ''', (selected_file, col_name, semantic_tag, session_id))
                    conn.commit()
                    conn.close()
                    st.success("✅ Schema saved.")

                st.subheader("📜 Current Saved Schema")
                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    SELECT column_name, semantic_tag, timestamp FROM csv_column_schemas
                    WHERE filename = ? ORDER BY timestamp DESC
                ''', (selected_file,))
                saved_schema = c.fetchall()
                conn.close()

                if saved_schema:
                    for s in saved_schema:
                        st.write(f"{s[0]} ➝ **{s[1]}** (Saved: {s[2]})")
                else:
                    st.info("No schema saved for this file yet.")

            except Exception as e:
                st.error(f"❌ Failed to preview file: {e}")

        elif selected_file.endswith(".pcap"):
            st.info("PCAP preview not yet supported — decoder coming soon.")
        else:
            st.warning("Unknown file format. Cannot preview.")
    else:
        st.warning("No files found in upload directory.")
# ==============================
# Part 15: File Search + Session Filter Browser
# ==============================

if page == "Session Browser":
    st.divider()
    st.subheader("🔍 Search Uploaded Files by Tags or Session")

    conn = get_connection()
    c = conn.cursor()

    # Fetch all distinct sessions
    c.execute("SELECT DISTINCT session_id FROM file_tags ORDER BY timestamp DESC")
    session_options = [row[0] for row in c.fetchall()]

    # Fetch all distinct tag types
    c.execute("SELECT DISTINCT tag_type FROM file_tags")
    tag_type_options = [row[0] for row in c.fetchall()]

    with st.form("file_search_form"):
        col1, col2 = st.columns(2)
        with col1:
            search_session = st.selectbox("Filter by Session ID", ["All"] + session_options)
            search_name = st.text_input("Search by Filename or Test Name (partial)")
        with col2:
            search_type = st.selectbox("Filter by Tag Type", ["All"] + tag_type_options)

        run_search = st.form_submit_button("🔍 Run Search")

    if run_search:
        query = "SELECT filename, session_id, test_name, tag_type, timestamp FROM file_tags WHERE 1=1"
        params = []

        if search_session != "All":
            query += " AND session_id = ?"
            params.append(search_session)

        if search_type != "All":
            query += " AND tag_type = ?"
            params.append(search_type)

        if search_name:
            query += " AND (filename LIKE ? OR test_name LIKE ?)"
            like_term = f"%{search_name}%"
            params.extend([like_term, like_term])

        query += " ORDER BY timestamp DESC"

        c.execute(query, tuple(params))
        results = c.fetchall()

        st.divider()
        st.subheader(f"📁 {len(results)} Matching File(s)")

        if results:
            for r in results:
                st.markdown(f"- **📁 {r[0]}**  ")
                st.markdown(f"    • Session: {r[1]}  ")
                st.markdown(f"    • Test Name: {r[2]}  ")
                st.markdown(f"    • Type: {r[3]}  ")
                st.markdown(f"    • Timestamp: {r[4]}")
                st.divider()
        else:
            st.warning("No matching files found.")

    conn.close()
# ==============================
# End of Part 15 – File Search + Session Filter
# ==============================

# ==============================
# Part 16: CSV Table Annotator + Row Highlight Tagger
# ==============================

if page == "Preview":
    st.divider()
    st.subheader("🔎 Row Tagging & Annotation")

    if selected_file.endswith(".csv"):
        try:
            df = pd.read_csv(file_path)
            max_rows = st.slider("Max Rows to Display", 10, 500, 50)
            st.dataframe(df.head(max_rows))

            tag_rows = st.multiselect("Select row indices to tag", df.index.tolist())
            annotation = st.text_area("Tag Notes / Annotation")

            if st.button("💾 Save Row Tags"):
                if tag_rows and annotation:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute('''
                        CREATE TABLE IF NOT EXISTS csv_row_tags (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            filename TEXT,
                            row_index INTEGER,
                            annotation TEXT,
                            session_id TEXT,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    for row_id in tag_rows:
                        c.execute('''
                            INSERT INTO csv_row_tags (filename, row_index, annotation, session_id)
                            VALUES (?, ?, ?, ?)
                        ''', (selected_file, row_id, annotation, session_id))
                    conn.commit()
                    conn.close()
                    st.success("✅ Row annotations saved.")
                else:
                    st.warning("⚠️ Select rows and enter annotation.")

            st.divider()
            st.subheader("📋 Existing Row Tags")
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                SELECT row_index, annotation, timestamp FROM csv_row_tags
                WHERE filename = ? ORDER BY timestamp DESC
            ''', (selected_file,))
            tagged_rows = c.fetchall()
            conn.close()

            if tagged_rows:
                for tag in tagged_rows:
                    st.markdown(f"🔖 Row {tag[0]} ➝ {tag[1]} (Tagged: {tag[2]})")
            else:
                st.info("No row-level tags found for this file.")

        except Exception as e:
            st.error(f"❌ Failed to load file for tagging: {e}")

# ==============================
# End of Part 16 – CSV Row Tagger + Annotation
# ==============================
# ==============================
# Part 17: Latency + Timestamp Grapher
# ==============================

if page == "Preview":
    st.divider()
    st.subheader("📈 Latency & Timestamp Visualizer")

    if selected_file.endswith(".csv"):
        try:
            df = pd.read_csv(file_path)
            available_columns = df.columns.tolist()

            col1, col2 = st.columns(2)
            with col1:
                timestamp_col = st.selectbox("Select Timestamp Column", available_columns, key="ts_col")
            with col2:
                latency_col = st.selectbox("Select Latency Column", available_columns, key="lat_col")

            if timestamp_col and latency_col:
                plot_df = df[[timestamp_col, latency_col]].copy()

                # Try converting timestamp
                try:
                    plot_df[timestamp_col] = pd.to_datetime(plot_df[timestamp_col])
                except:
                    st.warning("⚠️ Could not parse timestamp column. Plot may not reflect accurate time.")

                plot_df = plot_df.dropna()
                plot_df = plot_df.sort_values(by=timestamp_col)

                st.line_chart(plot_df.set_index(timestamp_col))
                st.success("✅ Latency chart rendered.")

        except Exception as e:
            st.error(f"❌ Failed to render chart: {e}")

# ==============================
# End of Part 17 – Latency Graph Tool
# ==============================
# ==============================
# Part 18: CSV Column Stats + Histogram Analyzer
# ==============================

if page == "Preview":
    st.divider()
    st.subheader("📊 Column Stats & Histogram Viewer")

    if selected_file.endswith(".csv"):
        try:
            df = pd.read_csv(file_path)

            numeric_columns = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
            if not numeric_columns:
                st.info("No numeric columns found for histogram analysis.")
            else:
                selected_numeric = st.selectbox("Select a numeric column for analysis", numeric_columns)

                if selected_numeric:
                    col_data = df[selected_numeric].dropna()

                    st.markdown(f"### 📈 Histogram: {selected_numeric}")
                    st.bar_chart(col_data.value_counts().sort_index())

                    st.markdown("### 📊 Basic Stats")
                    st.write(f"- Count: {len(col_data)}")
                    st.write(f"- Mean: {col_data.mean():.2f}")
                    st.write(f"- Median: {col_data.median():.2f}")
                    st.write(f"- Std Dev: {col_data.std():.2f}")
                    st.write(f"- Min: {col_data.min()}")
                    st.write(f"- Max: {col_data.max()}")

        except Exception as e:
            st.error(f"❌ Failed to compute column stats: {e}")
# ==============================
# Part 19: PCAP File Uploader + Metadata Extractor
# ==============================

import datetime

if page == "Upload":
    st.title("📤 Upload CSV, PCAP, or SBD")

    uploaded_file = st.file_uploader("Choose a CSV, PCAP, or SBD file", type=["csv", "pcap", "sbd"])

    if uploaded_file:
        apply_auto_tagging_on_upload(uploaded_file)

        if uploaded_file.name.endswith(".pcap"):
            st.divider()
            st.subheader("🧾 PCAP File Details")

            pcap_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            size_bytes = len(uploaded_file.getvalue())
            timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            file_info = {
                "Filename": uploaded_file.name,
                "Size (bytes)": size_bytes,
                "Saved Path": pcap_path,
                "Timestamp": timestamp_now
            }

            st.json(file_info)

            st.subheader("Packet Decoder Preview")
            st.info("⚙️ PCAP decoding and packet analysis is under development for v7.3. This view will soon include packet summaries, filters, and protocol hooks.")

            # Store basic info in DB (future use)
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS pcap_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    path TEXT,
                    size INTEGER,
                    timestamp TEXT
                )
            ''')
            c.execute('''
                INSERT INTO pcap_files (filename, path, size, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (
                uploaded_file.name,
                pcap_path,
                size_bytes,
                datetime.datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()

            st.success("✅ PCAP file metadata saved.")
# ==============================
# Part 20: PCAP Decoder + Packet Summary Table
# ==============================

from scapy.all import rdpcap, IP, TCP, UDP

if page == "Preview":
    if selected_file.endswith(".pcap"):
        st.divider()
        st.subheader("📦 PCAP Packet Summary")

        try:
            pcap_path = os.path.join(UPLOAD_DIR, selected_file)
            packets = rdpcap(pcap_path)

            summary_data = []

            for pkt in packets:
                if IP in pkt:
                    ip_layer = pkt[IP]
                    proto = ip_layer.proto
                    protocol_name = {6: "TCP", 17: "UDP"}.get(proto, str(proto))

                    src_ip = ip_layer.src
                    dst_ip = ip_layer.dst
                    pkt_len = len(pkt)

                    src_port = dst_port = None
                    if TCP in pkt:
                        src_port = pkt[TCP].sport
                        dst_port = pkt[TCP].dport
                    elif UDP in pkt:
                        src_port = pkt[UDP].sport
                        dst_port = pkt[UDP].dport

                    summary_data.append({
                        "Timestamp": datetime.datetime.fromtimestamp(pkt.time).strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "Source IP": src_ip,
                        "Destination IP": dst_ip,
                        "Protocol": protocol_name,
                        "Src Port": src_port,
                        "Dst Port": dst_port,
                        "Length": pkt_len
                    })

            if summary_data:
                df_summary = pd.DataFrame(summary_data)
                st.success(f"✅ Decoded {len(df_summary)} IP packets.")
                st.dataframe(df_summary)

                csv_download = df_summary.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Summary CSV",
                    data=csv_download,
                    file_name=f"{selected_file}_summary.csv",
                    mime='text/csv'
                )
            else:
                st.warning("⚠️ No IP packets found in this PCAP.")

        except Exception as e:
            st.error(f"❌ Failed to decode PCAP: {e}")

# ==============================
# End of Part 20 – PCAP Decoder
# ==============================
# ==============================
# Part 21: PCAP Packet Drilldown + Protocol Filters
# ==============================

if page == "Preview":
    if selected_file.endswith(".pcap"):
        st.divider()
        st.subheader("🔎 PCAP Packet Drilldown & Filters")

        try:
            pcap_path = os.path.join(UPLOAD_DIR, selected_file)
            packets = rdpcap(pcap_path)

            summary_data = []

            for pkt in packets:
                if IP in pkt:
                    ip_layer = pkt[IP]
                    proto = ip_layer.proto
                    protocol_name = {6: "TCP", 17: "UDP"}.get(proto, str(proto))

                    src_ip = ip_layer.src
                    dst_ip = ip_layer.dst
                    pkt_len = len(pkt)

                    src_port = dst_port = None
                    if TCP in pkt:
                        src_port = pkt[TCP].sport
                        dst_port = pkt[TCP].dport
                    elif UDP in pkt:
                        src_port = pkt[UDP].sport
                        dst_port = pkt[UDP].dport

                    summary_data.append({
                        "Timestamp": datetime.datetime.fromtimestamp(pkt.time).strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "Source IP": src_ip,
                        "Destination IP": dst_ip,
                        "Protocol": protocol_name,
                        "Src Port": src_port,
                        "Dst Port": dst_port,
                        "Length": pkt_len,
                        "Full Packet": pkt.summary()
                    })

            if summary_data:
                df_packets = pd.DataFrame(summary_data)

                st.success(f"✅ Loaded {len(df_packets)} packets with IP layers.")

                # Filter Section
                st.subheader("🧹 Filter Packets")
                col1, col2 = st.columns(2)
                with col1:
                    protocol_filter = st.selectbox("Protocol Filter", ["All", "TCP", "UDP"])
                    ip_search = st.text_input("Search IP Address (partial match)")
                with col2:
                    port_search = st.text_input("Search Port Number")

                filtered_df = df_packets.copy()

                if protocol_filter != "All":
                    filtered_df = filtered_df[filtered_df["Protocol"] == protocol_filter]

                if ip_search:
                    filtered_df = filtered_df[
                        filtered_df["Source IP"].str.contains(ip_search) |
                        filtered_df["Destination IP"].str.contains(ip_search)
                    ]

                if port_search:
                    filtered_df = filtered_df[
                        (filtered_df["Src Port"] == int(port_search)) |
                        (filtered_df["Dst Port"] == int(port_search))
                    ]

                st.info(f"🔎 {len(filtered_df)} packets match your filter criteria.")

                st.dataframe(filtered_df[[
                    "Timestamp", "Source IP", "Destination IP", "Protocol", "Src Port", "Dst Port", "Length"
                ]])

                st.divider()

                # Expandable Drilldown Section
                st.subheader("📦 Packet Drilldown (Expand Details)")

                for idx, row in filtered_df.iterrows():
                    with st.expander(f"Packet #{idx} | {row['Source IP']} ➔ {row['Destination IP']} ({row['Protocol']})"):
                        st.code(row["Full Packet"], language="bash")

                # Download filtered results
                csv_download = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Filtered Packets CSV",
                    data=csv_download,
                    file_name=f"{selected_file}_filtered_packets.csv",
                    mime='text/csv'
                )
            else:
                st.warning("⚠️ No IP packets found for detailed view.")

        except Exception as e:
            st.error(f"❌ Failed to process PCAP for drilldown: {e}")

# ==============================
# End of Part 21 – PCAP Drilldown & Filter
# ==============================
# ==============================
# Part 22: PCAP TCP Session Rebuilder
# ==============================

if page == "Preview":
    if selected_file.endswith(".pcap"):
        st.divider()
        st.subheader("🔗 TCP Session Rebuilder (Prototype)")

        try:
            pcap_path = os.path.join(UPLOAD_DIR, selected_file)
            packets = rdpcap(pcap_path)

            tcp_sessions = {}

            for pkt in packets:
                if TCP in pkt and IP in pkt:
                    ip_layer = pkt[IP]
                    tcp_layer = pkt[TCP]

                    # Build session key (src_ip:src_port -> dst_ip:dst_port)
                    session_key = f"{ip_layer.src}:{tcp_layer.sport} ➔ {ip_layer.dst}:{tcp_layer.dport}"

                    if session_key not in tcp_sessions:
                        tcp_sessions[session_key] = []

                    tcp_sessions[session_key].append({
                        "seq": tcp_layer.seq,
                        "ack": tcp_layer.ack,
                        "payload_len": len(tcp_layer.payload),
                        "timestamp": datetime.datetime.fromtimestamp(pkt.time).strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "summary": pkt.summary(),
                        "payload_hex": bytes(tcp_layer.payload).hex()
                    })

            if tcp_sessions:
                st.success(f"✅ Found {len(tcp_sessions)} TCP sessions.")

                selected_session = st.selectbox("Select TCP Session", list(tcp_sessions.keys()))

                if selected_session:
                    session_packets = sorted(tcp_sessions[selected_session], key=lambda x: x["seq"])

                    st.subheader(f"📋 TCP Session: {selected_session}")
                    st.markdown(f"Total Packets: **{len(session_packets)}**")

                    for idx, pkt in enumerate(session_packets):
                        with st.expander(f"Packet #{idx+1} | Seq: {pkt['seq']} | Ack: {pkt['ack']} | Len: {pkt['payload_len']}"):
                            st.write(f"⏱️ Timestamp: {pkt['timestamp']}")
                            st.code(pkt['summary'], language="bash")
                            if pkt['payload_len'] > 0:
                                st.code(pkt['payload_hex'], language="bash")
                            else:
                                st.info("No payload in this segment.")

            else:
                st.warning("⚠️ No TCP sessions found in this PCAP.")

        except Exception as e:
            st.error(f"❌ Failed to rebuild TCP sessions: {e}")

# ==============================
# End of Part 22 – TCP Session Rebuilder
# ==============================
# ==============================
# Part 23: TCP Stream Reassembler + Gap Detector
# ==============================

if page == "Preview":
    if selected_file.endswith(".pcap"):
        st.divider()
        st.subheader("🛠 TCP Stream Reassembler + Gap Detector")

        try:
            pcap_path = os.path.join(UPLOAD_DIR, selected_file)
            packets = rdpcap(pcap_path)

            tcp_streams = {}

            for pkt in packets:
                if TCP in pkt and IP in pkt:
                    ip_layer = pkt[IP]
                    tcp_layer = pkt[TCP]

                    session_key = f"{ip_layer.src}:{tcp_layer.sport} ➔ {ip_layer.dst}:{tcp_layer.dport}"

                    if session_key not in tcp_streams:
                        tcp_streams[session_key] = []

                    tcp_streams[session_key].append({
                        "seq": tcp_layer.seq,
                        "ack": tcp_layer.ack,
                        "payload": bytes(tcp_layer.payload),
                        "timestamp": datetime.datetime.fromtimestamp(pkt.time).strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "summary": pkt.summary()
                    })

            if tcp_streams:
                st.success(f"✅ Found {len(tcp_streams)} TCP streams.")

                selected_stream = st.selectbox("Select TCP Stream to Reassemble", list(tcp_streams.keys()), key="stream_select")

                if selected_stream:
                    stream_packets = sorted(tcp_streams[selected_stream], key=lambda x: x["seq"])

                    reconstructed_bytes = bytearray()
                    gap_report = []
                    expected_seq = None

                    for pkt in stream_packets:
                        seq = pkt["seq"]
                        payload = pkt["payload"]

                        if expected_seq is not None and seq > expected_seq:
                            gap_size = seq - expected_seq
                            gap_report.append({
                                "gap_start_seq": expected_seq,
                                "gap_end_seq": seq - 1,
                                "gap_size": gap_size
                            })
                            # Optionally pad with zeros
                            reconstructed_bytes.extend(b"\x00" * gap_size)

                        reconstructed_bytes.extend(payload)
                        expected_seq = seq + len(payload)

                    st.success(f"✅ Stream reassembled ({len(reconstructed_bytes)} bytes).")

                    # Display hex or ascii
                    display_mode = st.radio("Display Mode", ["Hex", "ASCII"], horizontal=True)

                    if display_mode == "Hex":
                        hex_stream = ' '.join(f'{b:02X}' for b in reconstructed_bytes[:1024])
                        st.code(hex_stream + (" ..." if len(reconstructed_bytes) > 1024 else ""), language="bash")
                    else:
                        try:
                            ascii_text = reconstructed_bytes.decode('utf-8', errors='replace')
                            st.text_area("ASCII View", ascii_text[:5000] + ("\n..." if len(ascii_text) > 5000 else ""), height=300)
                        except Exception as decode_error:
                            st.error(f"❌ ASCII decode error: {decode_error}")

                    st.divider()
                    st.subheader("🚨 Gap Report")

                    if gap_report:
                        df_gaps = pd.DataFrame(gap_report)
                        st.dataframe(df_gaps)

                        st.warning(f"⚠️ {len(gap_report)} gap(s) detected during reassembly.")
                    else:
                        st.success("✅ No gaps detected. Stream appears complete.")

                    st.divider()

                    # Download reconstructed stream
                    st.subheader("📥 Download Reconstructed Stream")
                    st.download_button(
                        label="Download as Binary",
                        data=reconstructed_bytes,
                        file_name=f"{selected_stream.replace(' ', '_')}_reconstructed.bin",
                        mime="application/octet-stream"
                    )

            else:
                st.warning("⚠️ No TCP streams found for reassembly.")

        except Exception as e:
            st.error(f"❌ Failed to reassemble TCP streams: {e}")

# ==============================
# End of Part 23 – TCP Stream Reassembler + Gap Detector
# ==============================
# ==============================
# Part 24: TCP Payload Extractor by Port Filter
# ==============================

if page == "Preview":
    if selected_file.endswith(".pcap"):
        st.divider()
        st.subheader("🎯 TCP Payload Extractor by Port")

        try:
            pcap_path = os.path.join(UPLOAD_DIR, selected_file)
            packets = rdpcap(pcap_path)

            port_payloads = {}

            for pkt in packets:
                if TCP in pkt and IP in pkt:
                    sport = pkt[TCP].sport
                    dport = pkt[TCP].dport
                    payload = bytes(pkt[TCP].payload)

                    for port in [sport, dport]:
                        if port not in port_payloads:
                            port_payloads[port] = bytearray()
                        port_payloads[port].extend(payload)

            if port_payloads:
                st.success(f"✅ Found TCP payloads for {len(port_payloads)} ports.")
                selected_port = st.selectbox("Select Port to View Payload", sorted(port_payloads.keys()))

                if selected_port in port_payloads:
                    port_data = port_payloads[selected_port]

                    st.markdown(f"### Port {selected_port} – Total Bytes: {len(port_data)}")

                    view_mode = st.radio("Display Format", ["Hex", "ASCII"], horizontal=True, key="port_display")

                    if view_mode == "Hex":
                        hex_view = ' '.join(f'{b:02X}' for b in port_data[:1024])
                        st.code(hex_view + (" ..." if len(port_data) > 1024 else ""), language="bash")
                    else:
                        try:
                            ascii_view = port_data.decode('utf-8', errors='replace')
                            st.text_area("ASCII Output", ascii_view[:5000] + ("\n..." if len(ascii_view) > 5000 else ""), height=300)
                        except Exception as decode_err:
                            st.error(f"❌ Decode error: {decode_err}")

                    st.download_button(
                        label="📥 Download Full Payload",
                        data=port_data,
                        file_name=f"port_{selected_port}_payload.bin",
                        mime="application/octet-stream"
                    )

            else:
                st.warning("⚠️ No TCP payloads found by port.")

        except Exception as e:
            st.error(f"❌ Error processing port payloads: {e}")

# ==============================
# End of Part 24 – TCP Payload Extractor
# ==============================
# ==============================
# Part 25: TCP Stream Sequence Timeline Grapher
# ==============================

if page == "Preview":
    if selected_file.endswith(".pcap"):
        st.divider()
        st.subheader("📈 TCP Stream Sequence Timeline Grapher")

        try:
            pcap_path = os.path.join(UPLOAD_DIR, selected_file)
            packets = rdpcap(pcap_path)

            tcp_streams = {}

            for pkt in packets:
                if TCP in pkt and IP in pkt:
                    ip_layer = pkt[IP]
                    tcp_layer = pkt[TCP]
                    session_key = f"{ip_layer.src}:{tcp_layer.sport} ➔ {ip_layer.dst}:{tcp_layer.dport}"

                    if session_key not in tcp_streams:
                        tcp_streams[session_key] = []

                    tcp_streams[session_key].append({
                        "seq": tcp_layer.seq,
                        "ack": tcp_layer.ack,
                        "payload_len": len(tcp_layer.payload),
                        "timestamp": datetime.datetime.fromtimestamp(pkt.time)
                    })

            if tcp_streams:
                st.success(f"✅ Found {len(tcp_streams)} TCP streams for timeline analysis.")

                selected_timeline_stream = st.selectbox("Select TCP Stream for Sequence Timeline", list(tcp_streams.keys()), key="timeline_select")

                if selected_timeline_stream:
                    timeline_packets = sorted(tcp_streams[selected_timeline_stream], key=lambda x: x["timestamp"])

                    st.subheader(f"📈 Sequence Number vs Time: {selected_timeline_stream}")

                    seq_numbers = [pkt["seq"] for pkt in timeline_packets]
                    timestamps = [pkt["timestamp"] for pkt in timeline_packets]

                    if seq_numbers and timestamps:
                        timeline_df = pd.DataFrame({
                            "Timestamp": timestamps,
                            "Sequence Number": seq_numbers
                        })

                        st.line_chart(timeline_df.set_index("Timestamp"))
                        st.success("✅ Timeline graphed successfully.")
                    else:
                        st.warning("⚠️ No valid sequence numbers found for this stream.")

            else:
                st.warning("⚠️ No TCP streams found for timeline plotting.")

        except Exception as e:
            st.error(f"❌ Failed to generate TCP stream timeline: {e}")

# ==============================
# End of Part 25 – TCP Stream Sequence Timeline Grapher
# ==============================
# ==============================
# Part 26: TCP Retransmission Detector + Timeline Overlay
# ==============================

if page == "Preview":
    if selected_file.endswith(".pcap"):
        st.divider()
        st.subheader("🚨 TCP Retransmission Detector + Timeline Overlay")

        try:
            pcap_path = os.path.join(UPLOAD_DIR, selected_file)
            packets = rdpcap(pcap_path)

            tcp_streams = {}

            for pkt in packets:
                if TCP in pkt and IP in pkt:
                    ip_layer = pkt[IP]
                    tcp_layer = pkt[TCP]
                    session_key = f"{ip_layer.src}:{tcp_layer.sport} ➔ {ip_layer.dst}:{tcp_layer.dport}"

                    if session_key not in tcp_streams:
                        tcp_streams[session_key] = []

                    tcp_streams[session_key].append({
                        "seq": tcp_layer.seq,
                        "ack": tcp_layer.ack,
                        "payload_len": len(tcp_layer.payload),
                        "timestamp": datetime.datetime.fromtimestamp(pkt.time)
                    })

            if tcp_streams:
                st.success(f"✅ Found {len(tcp_streams)} TCP streams.")

                selected_retx_stream = st.selectbox("Select Stream for Retransmission Analysis", list(tcp_streams.keys()), key="retrans_select")

                if selected_retx_stream:
                    stream_packets = sorted(tcp_streams[selected_retx_stream], key=lambda x: x["timestamp"])

                    seq_seen = set()
                    retransmissions = []
                    timeline_seq = []
                    timeline_time = []

                    for pkt in stream_packets:
                        seq = pkt["seq"]
                        ts = pkt["timestamp"]

                        timeline_seq.append(seq)
                        timeline_time.append(ts)

                        if seq in seq_seen:
                            retransmissions.append((ts, seq))
                        else:
                            seq_seen.add(seq)

                    st.subheader(f"📈 Sequence Number Timeline with Retransmissions: {selected_retx_stream}")

                    # Plotting
                    import matplotlib.pyplot as plt

                    fig, ax = plt.subplots(figsize=(10,6))

                    # Main Sequence Plot
                    ax.plot(timeline_time, timeline_seq, marker='o', linestyle='-', label="TCP Sequence")

                    # Mark Retransmissions
                    if retransmissions:
                        retx_times, retx_seqs = zip(*retransmissions)
                        ax.scatter(retx_times, retx_seqs, color='red', label="Retransmissions", zorder=5)

                    ax.set_xlabel("Timestamp")
                    ax.set_ylabel("Sequence Number")
                    ax.set_title(f"TCP Stream: {selected_retx_stream}")
                    ax.legend()
                    ax.grid(True)

                    st.pyplot(fig)

                    if retransmissions:
                        st.warning(f"⚠️ Detected {len(retransmissions)} retransmissions in this stream.")
                        st.subheader("📋 Retransmission Events")
                        for ts, seq in retransmissions:
                            st.markdown(f"- 🔴 {ts} | Sequence: {seq}")
                    else:
                        st.success("✅ No retransmissions detected.")

            else:
                st.warning("⚠️ No TCP streams found.")

        except Exception as e:
            st.error(f"❌ Failed to analyze retransmissions: {e}")

# ==============================
# End of Part 26 – TCP Retransmission Detector
# ==============================