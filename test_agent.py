#!/usr/bin/env python3
"""Runner for backend/test_agent.py from workspace root"""
import os
import sys

# Ensure UTF-8 output encoding across platforms
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.test_agent import run_tests

if __name__ == "__main__":
    run_tests()
