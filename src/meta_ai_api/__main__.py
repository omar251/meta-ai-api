#!/usr/bin/env python3
"""
Main entry point for running meta_ai_api as a module.

This allows running: python -m meta_ai_api
"""

import sys
from .cli import main

if __name__ == "__main__":
    # Forward all arguments to the CLI
    sys.exit(main())