"""Finvista application package (install name: finvista, source dir: src/)."""

import sys
import os

# Force UTF-8 encoding for stdout/stderr on Windows to handle emoji characters
if sys.platform == 'win32':
    try:
        # Configure console for UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        
        # Set environment variable for UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    except Exception:
        pass

