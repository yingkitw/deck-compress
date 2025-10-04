#!/usr/bin/env python3
"""
Run the Deck Compress Web Application
"""

import uvicorn
from pathlib import Path
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    print("🚀 Starting Deck Compress Web Application...")
    print("📁 Web interface will be available at: http://localhost:8000")
    print("📊 API documentation at: http://localhost:8000/docs")
    print("🛑 Press Ctrl+C to stop the server")
    print()
    
    uvicorn.run(
        "web_app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
