#!/usr/bin/env python3
"""
Vercel Deployment Validation Script

Verifies that everything is ready for Vercel deployment
"""

import os
import sys
import json

def check_file_exists(filepath, name):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"  ✅ {name}")
        return True
    else:
        print(f"  ❌ {name} - NOT FOUND")
        return False

def check_syntax(filepath):
    """Check Python file syntax"""
    try:
        import py_compile
        py_compile.compile(filepath, doraise=True)
        print(f"  ✅ {filepath} - syntax OK")
        return True
    except Exception as e:
        print(f"  ❌ {filepath} - syntax error: {e}")
        return False

def main():
    print("\n" + "=" * 70)
    print("  VERCEL DEPLOYMENT VALIDATION")
    print("=" * 70 + "\n")
    
    all_ok = True
    
    # Check required files
    print("1️⃣  Required Files")
    print("-" * 70)
    required_files = {
        "app.py": "Main Flask application",
        "requirements.txt": "Python dependencies",
        "vercel.json": "Vercel configuration",
        ".vercelignore": "Files to ignore in deployment",
        "templates/": "HTML templates directory",
        "static/": "Static assets directory"
    }
    
    for filepath, description in required_files.items():
        if not check_file_exists(filepath, f"{filepath} - {description}"):
            all_ok = False
    
    # Check syntax
    print("\n2️⃣  Python Syntax Check")
    print("-" * 70)
    python_files = [
        "app.py",
        "supabase_client.py",
        "feature_flag_client.py",
        "enhanced_ast_analyzer.py",
    ]
    
    for pyfile in python_files:
        if os.path.exists(pyfile) and not check_syntax(pyfile):
            all_ok = False
    
    # Check dependencies
    print("\n3️⃣  Dependencies (requirements.txt)")
    print("-" * 70)
    try:
        with open("requirements.txt", "r") as f:
            deps = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        required_deps = ["flask", "flask-cors", "pyyaml", "supabase"]
        
        for dep in required_deps:
            found = any(dep in d.lower() for d in deps)
            if found:
                print(f"  ✅ {dep}")
            else:
                print(f"  ❌ {dep} - MISSING")
                all_ok = False
        
        print(f"  ℹ️  Total packages: {len(deps)}")
    except Exception as e:
        print(f"  ❌ Error reading requirements.txt: {e}")
        all_ok = False
    
    # Check vercel.json
    print("\n4️⃣  Vercel Configuration (vercel.json)")
    print("-" * 70)
    try:
        with open("vercel.json", "r") as f:
            vercel_config = json.load(f)
        
        checks = [
            ("version" in vercel_config, "Version field"),
            ("builds" in vercel_config, "Builds configuration"),
            ("routes" in vercel_config, "Routes configuration"),
            (vercel_config.get("builds", [{}])[0].get("src") == "app.py", "app.py as source"),
            (vercel_config.get("builds", [{}])[0].get("use") == "@vercel/python", "Python runtime"),
        ]
        
        for check, name in checks:
            if check:
                print(f"  ✅ {name}")
            else:
                print(f"  ❌ {name}")
                all_ok = False
    except Exception as e:
        print(f"  ❌ Error reading vercel.json: {e}")
        all_ok = False
    
    # Check imports
    print("\n5️⃣  Module Imports")
    print("-" * 70)
    try:
        import app as app_module
        print(f"  ✅ Flask app imports successfully")
        print(f"  ✅ App name: {app_module.app.name}")
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        all_ok = False
    except Exception as e:
        print(f"  ⚠️  {e}")
    
    # Check environment setup
    print("\n6️⃣  Environment Variables (in Vercel)")
    print("-" * 70)
    required_env = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "FLASK_ENV",
        "FLASK_DEBUG"
    ]
    
    print("  ⚠️  These should be set in Vercel dashboard:")
    for env_var in required_env:
        print(f"     - {env_var}")
    
    # Summary
    print("\n" + "=" * 70)
    if all_ok:
        print("  ✅ READY FOR DEPLOYMENT")
        print("=" * 70)
        print("\n  Next steps:")
        print("  1. Set environment variables in Vercel dashboard")
        print("  2. Run: vercel login")
        print("  3. Run: vercel --prod")
        print("\n")
        return 0
    else:
        print("  ❌ DEPLOYMENT NOT READY")
        print("=" * 70)
        print("\n  Please fix the issues above before deploying.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
