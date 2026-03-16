import sys
import os

print("Verifying Python syntax...")

try:
    # 1. Check generate_prompt
    print("Checking execution/generate_prompt.py...")
    sys.path.append(os.path.abspath("execution"))
    import generate_prompt
    print("✅ generate_prompt imported successfully.")

    # 2. Check app.py compilation
    print("Checking app.py syntax...")
    import py_compile
    py_compile.compile("app.py", doraise=True)
    print("✅ app.py compiled successfully.")
    
    print("ALL CHECKS PASSED. The files are clean.")

except Exception as e:
    print(f"❌ SYNTAX VERIFICATION FAILED: {e}")
    sys.exit(1)
