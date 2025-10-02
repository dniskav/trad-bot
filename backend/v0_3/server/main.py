#!/usr/bin/env python3  
"""
Server Package - Entry Point
Trading Server - Independent package entry point
"""

import sys
import os
from pathlib import Path

# Add shared package to path  
server_dir = Path(__file__).parent
shared_dir = server_dir.parent / "shared"
sys.path.insert(0, str(shared_dir))

if __name__ == "__main__":
    import uvicorn
    from .app import app
    
    print("🚀 Starting Server Package (Trading Server)")
    print(f"📁 Server Directory: {server_dir}")
    print(f"📁 Shared Directory: {shared_dir}")
    
    uvicorn.run(
        app,
        host="127.0.0.1", 
        port=8200,
        log_level="info"
    )