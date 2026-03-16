
import sqlite3
import os

DB_PATH = 'users.db'

def check_users():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute("SELECT username, email, credits, is_admin FROM users")
        users = c.fetchall()
        
        print(f"found {len(users)} users:")
        found = False
        for u in users:
            print(f"- User: {u[0]}, Email: {u[1]}, Credits: {u[2]}, Admin: {u[3]}")
            if u[0] == 'jordan.highendestates@gmail.com' or u[1] == 'jordan.highendestates@gmail.com':
                found = True
        
        if found:
            print("\n✅ User 'jordan.highendestates@gmail.com' FOUND in database.")
        else:
            print("\n❌ User 'jordan.highendestates@gmail.com' NOT FOUND in users table.")

        # Check Allowlist
        c.execute("SELECT email, active FROM allowlist WHERE email=?", ('jordan.highendestates@gmail.com',))
        row = c.fetchone()
        if row:
            print(f"✅ Email found in Allowlist: Active={row[1]}")
        else:
            print(f"❌ Email NOT found in Allowlist")
            
    except Exception as e:
        print(f"Error reading database: {e}")
        # Try to print schema
        try:
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            print("Tables:", c.fetchall())
        except:
            pass
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_users()
