#!/usr/bin/env python3
"""
Test script to identify import issues in the Flask app.
This helps diagnose why Gunicorn workers fail to boot.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all critical imports to identify issues"""
    
    print("Testing imports...")
    
    try:
        print("1. Testing basic Flask imports...")
        from flask import Flask
        print("   ✓ Flask imported successfully")
        
        print("2. Testing app factory import...")
        from app import create_app
        print("   ✓ create_app imported successfully")
        
        print("3. Testing database import...")
        from app import db
        print("   ✓ Database imported successfully")
        
        print("4. Testing model imports...")
        from app.models import Tenant, User, Post, Category, Tag, MediaFile, Setting
        print("   ✓ All models imported successfully")
        
        print("5. Testing blueprint imports...")
        from app.blueprints import main, auth, dashboard, api, admin
        print("   ✓ All blueprints imported successfully")
        
        print("6. Testing app creation...")
        app = create_app('production')
        print("   ✓ App created successfully")
        
        print("7. Testing app context...")
        with app.app_context():
            print("   ✓ App context works")
        
        print("\n🎉 All imports successful! The app should work.")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"\n❌ General Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_imports()
    sys.exit(0 if success else 1)