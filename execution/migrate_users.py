import sqlite3
import json
import os
import time

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, "users.json")
DB_PATH = os.path.join(BASE_DIR, "users.db")

def create_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create Users Table
    # Added last_reset_date for monthly credit cycling
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            credits INTEGER DEFAULT 0,
            created_at REAL,
            last_reset_date TEXT
        )
    ''')
    
    # Create Allowlist Table (for future step)
    c.execute('''
        CREATE TABLE IF NOT EXISTS allowlist (
            email TEXT PRIMARY KEY,
            name TEXT,
            active INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    return conn

def migrate():
    if not os.path.exists(JSON_PATH):
        print(f"❌ No users.json found at {JSON_PATH}")
        return

    print(f"📂 Reading {JSON_PATH}...")
    with open(JSON_PATH, 'r') as f:
        try:
            users_data = json.load(f)
        except json.JSONDecodeError:
            print("❌ users.json is corrupt.")
            return

    conn = create_db()
    c = conn.cursor()
    
    count = 0
    for username, data in users_data.items():
        # Check if exists
        c.execute("SELECT username FROM users WHERE username=?", (username,))
        if c.fetchone():
            print(f"⚠️ Skipping {username} (already exists)")
            continue
            
        try:
            c.execute('''
                INSERT INTO users (username, password_hash, salt, role, credits, created_at, last_reset_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('username', username),
                data.get('hash', ''),
                data.get('salt', ''),
                data.get('role', 'viewer'),
                data.get('credits', 0),
                data.get('created_at', time.time()),
                None  # No reset date yet
            ))
            count += 1
            print(f"✅ Migrated {username}")
        except Exception as e:
            print(f"❌ Error migrating {username}: {e}")

    conn.commit()
    conn.close()
    print(f"\n🎉 Migration Complete! {count} users moved to SQLite.")

if __name__ == "__main__":
    migrate()
