#!/usr/bin/env python3
"""
CandyBarV2 — launch entry point.

Usage:
    python run.py
    # or equivalently:
    python -m app.main
"""
import runpy
import sys

if __name__ == "__main__":
    runpy.run_module("app.main", run_name="__main__", alter_sys=True)
