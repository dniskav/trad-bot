#!/usr/bin/env python3
"""
STM Package - Entry Point
Synthetic Trading Manager - Independent package entry point
"""

import sys
import os
from pathlib import Path

# Add shared package to path
stm_dir = Path(__file__).parent
shared_dir = stm_dir.parent / "shared"
sys.path.insert(0, str(shared_dir))

if __name__ == "__main__":
    import uvicorn
    from .app import app
    
    print("🚀 Starting STM Package (Synthetic Trading Manager)")
    print(f"📁 STM Directory: {stm_dir}")
    print(f"📁 Shared Directory: {shared_dir}")
    
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8100,
        log_level="info"
    )