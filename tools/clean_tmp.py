#!/usr/bin/env python3
"""Clean the tmp/ directory: remove all contents and recreate it empty."""

import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
TMP_DIR = os.path.join(PROJECT_ROOT, "tmp")

if os.path.exists(TMP_DIR):
    shutil.rmtree(TMP_DIR)
os.makedirs(TMP_DIR, exist_ok=True)
