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


def load_processed() -> set:
    """Load set of already-processed PDF filenames."""
    if not PROCESSED_FILE.exists():
        return set()
    with open(PROCESSED_FILE) as f:
        data = json.load(f)
    return set(data.get("processed", []))


def save_processed(processed: set) -> None:
    """Save set of processed PDF filenames."""
    with open(PROCESSED_FILE, "w") as f:
        json.dump({"processed": sorted(processed)}, f, indent=2)


def discover_pdfs() -> list[Path]:
    """Find all PDF files in the water bill directory."""
    if not WATER_BILL_DIR.exists():
        print(f"Error: {WATER_BILL_DIR} does not exist")
        sys.exit(1)
    return sorted(WATER_BILL_DIR.glob("*.pdf"))


def find_new_pdfs(all_pdfs: list[Path], processed: set, rebuild: bool) -> list[Path]:
    """Filter to only unprocessed PDFs (or all if rebuild=True)."""
    if rebuild:
        return all_pdfs
    return [p for p in all_pdfs if p.name not in processed]


def main():
    parser = argparse.ArgumentParser(description="Water Bill Data Refresh CLI")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse only, don't write files or commit")
    parser.add_argument("--no-push", action="store_true",
                        help="Commit but don't push to remote")
    parser.add_argument("--rebuild", action="store_true",
                        help="Ignore cache, reprocess all PDFs")

    args = parser.parse_args()

    # Discover PDFs
    all_pdfs = discover_pdfs()
    print(f"Found {len(all_pdfs)} PDF files in {WATER_BILL_DIR}")

    # Load tracking state
    processed = load_processed()
    new_pdfs = find_new_pdfs(all_pdfs, processed, args.rebuild)

    if not new_pdfs:
        print("No new PDFs to process")
        return

    print(f"Processing {len(new_pdfs)} new PDF(s):")
    for pdf in new_pdfs:
        print(f"  - {pdf.name}")


if __name__ == "__main__":
    main()
