from execution.auth import auth_mgr
import os

print(f"Checking for users.json: {os.path.exists('users.json')}")
print(f"Current Users: {list(auth_mgr.users.keys())}")

# Verify Admin
token, msg = auth_mgr.login("admin", os.getenv("APP_PASSWORD", "admin"))
print(f"Login Admin: {msg}")

if token:
    payload = auth_mgr.verify_token(token)
    print(f"Token Valid: {payload['username'] == 'admin'}")
else:
    print("Login Failed")
