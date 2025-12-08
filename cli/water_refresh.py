#!/usr/bin/env python3
"""
Water Bill Data Refresh CLI

Usage:
    python water_refresh.py              Process new PDFs, update JSON, commit & push
    python water_refresh.py --dry-run    Parse only, don't write files
    python water_refresh.py --no-push    Commit but don't push
    python water_refresh.py --rebuild    Ignore cache, reprocess all PDFs
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
WATER_BILL_DIR = DATA_DIR / "water_bill"
OUTPUT_FILE = DATA_DIR / "water-bills.json"
PROCESSED_FILE = DATA_DIR / ".water-processed.json"


def main():
    parser = argparse.ArgumentParser(description="Water Bill Data Refresh CLI")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse only, don't write files or commit")
    parser.add_argument("--no-push", action="store_true",
                        help="Commit but don't push to remote")
    parser.add_argument("--rebuild", action="store_true",
                        help="Ignore cache, reprocess all PDFs")

    args = parser.parse_args()

    print("Water Bill Refresh")
    print(f"  Data dir: {DATA_DIR}")
    print(f"  Dry run: {args.dry_run}")


if __name__ == "__main__":
    main()
