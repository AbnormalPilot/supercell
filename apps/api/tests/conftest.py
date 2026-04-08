"""Shared fixtures and path setup for all tests."""

import sys
import os

# Ensure project root is importable from all test files
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
