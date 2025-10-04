#!/usr/bin/env python3
"""
Test script to verify the web app works locally before deployment
"""

import sys
import os
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
src_path = current_dir.parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test if all required modules can be imported"""
    try:
        from deck_compress import process_single_file, CompressionProgress
        from rich.console import Console
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_fastapi_app():
    """Test if FastAPI app can be created"""
    try:
        from main import app
        print("✅ FastAPI app created successfully")
        return True
    except Exception as e:
        print(f"❌ FastAPI app error: {e}")
        return False

def test_directories():
    """Test if required directories exist"""
    current_dir = Path(__file__).parent
    static_dir = current_dir / "static"
    templates_dir = current_dir / "templates"
    
    if static_dir.exists():
        print("✅ Static directory exists")
    else:
        print("❌ Static directory missing")
        return False
        
    if templates_dir.exists():
        print("✅ Templates directory exists")
    else:
        print("❌ Templates directory missing")
        return False
        
    return True

def main():
    """Run all tests"""
    print("🧪 Testing Deck Compress Web App...")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")
    
    tests = [
        test_imports,
        test_fastapi_app,
        test_directories
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Fix issues before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
