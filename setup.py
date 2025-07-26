#!/usr/bin/env python3
"""
Setup script for NSE Technical Analysis System
Run: python setup.py
"""

import subprocess
import sys
import os

def run_command(command):
    """Run a shell command and return success status"""
    try:
        subprocess.run(command, shell=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("🚀 Setting up NSE Technical Analysis System...")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install requirements
    print("\n📦 Installing dependencies...")
    if run_command(f"{sys.executable} -m pip install -r requirements.txt"):
        print("✅ Dependencies installed successfully")
    else:
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Create necessary directories
    os.makedirs("data/cache", exist_ok=True)
    print("✅ Created data directories")
    
    # Test imports
    print("\n🧪 Testing core imports...")
    try:
        import yfinance
        import pandas
        import numpy
        import matplotlib
        print("✅ All core libraries imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run: python sandbox_analyzer.py")
    print("2. Choose option 1 to populate historical data")
    print("3. Choose option 2 for dynamic threshold analysis")
    print("\n💡 Check README.md for detailed usage instructions")

if __name__ == "__main__":
    main() 