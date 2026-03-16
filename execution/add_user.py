
import sqlite3
import os
import hashlib
import uuid
import time
from execution.auth import AuthManager

def add_jordan():
    auth = AuthManager()
    email = "jordan.highendestates@gmail.com"
    default_pass = "Start123!"
    
    print(f"--- Adding User: {email} ---")
    
    # 1. Add to Allowlist
    print("1. Adding to Allowlist...")
    if auth.add_to_allowlist(email, "Jordan"):
        print("   ✅ Added/Updated Allowlist")
    else:
        print("   ⚠️ Failed to update Allowlist (might already exist)")

    # 2. Check if User Exists
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username=?", (email,))
    if c.fetchone():
        print("   ⚠️ User already exists in 'users' table.")
        # Optional: Reset password?
        print("   🔄 Resetting password to default...")
        auth.reset_user_password(email, default_pass)
        print(f"   ✅ Password reset to: {default_pass}")
    else:
        # 3. Create User
        print("2. Creating User Account...")
        success, msg = auth.create_user(email, default_pass, role="admin") # Giving admin for now? Or viewer? Let's give Admin based on context of 'High End Estates'
        if success:
            print(f"   ✅ User created! Password: {default_pass}")
        else:
            print(f"   ❌ Failed to create user: {msg}")

    conn.close()

if __name__ == "__main__":
    add_jordan()
