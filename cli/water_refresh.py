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
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

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


def parse_water_bill(pdf_path: Path) -> dict:
    """
    Extract water bill data from a PDF.

    Returns dict with: month, label, bill_date, total, ccf,
                       sewer_volume, water_volume, fixed_costs, source_file

    Raises ValueError if parsing fails.
    """
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()

    if not text:
        raise ValueError(f"Could not extract text from {pdf_path.name}")

    # Extract bill date (format: MM/DD/YY in BillDate column)
    # Pattern: "BillDate DueDate..." followed by date line "11/26/24 12/19/24..."
    date_match = re.search(r"BillDate.*?\n(\d{1,2}/\d{1,2}/\d{2})", text, re.DOTALL)
    if not date_match:
        raise ValueError(f"Could not find bill date in {pdf_path.name}")

    bill_date_str = date_match.group(1)
    bill_date = datetime.strptime(bill_date_str, "%m/%d/%y")

    # Extract total amount due
    total_match = re.search(r"TotalAmountDue\s+([\d,]+\.\d{2})", text)
    if not total_match:
        # Try alternate pattern
        total_match = re.search(r"TOTALAMOUNTDUE\s+([\d,]+\.\d{2})", text)
    if not total_match:
        raise ValueError(f"Could not find total amount in {pdf_path.name}")

    total = float(total_match.group(1).replace(",", ""))

    # Extract consumption (CCF)
    ccf_match = re.search(r"CONSUMPTION\s+CCF.*?(\d+)\s*$", text, re.MULTILINE)
    if not ccf_match:
        # Try finding in meter reading line: "11/14/24 2" 4,837 4,943 106"
        ccf_match = re.search(r'\d{1,2}/\d{1,2}/\d{2}\s+\d+"\s+[\d,]+\s+[\d,]+\s+(\d+)', text)
    if not ccf_match:
        raise ValueError(f"Could not find CCF consumption in {pdf_path.name}")

    ccf = int(ccf_match.group(1))

    # Extract water consumption charge (format: "Water-Consumption@$2.56/ccf 271.36")
    # Need to skip the rate and get the final amount
    water_match = re.search(r"Water-Consumption@\$[\d.]+/ccf\s+([\d,]+\.\d{2})", text)
    if not water_match:
        raise ValueError(f"Could not find water consumption charge in {pdf_path.name}")

    water_volume = float(water_match.group(1).replace(",", ""))

    # Extract sewer volume charge (format: "Sewer-Volume@$7.92/ccf 776.16")
    sewer_match = re.search(r"Sewer-Volume@\$[\d.]+/ccf\s+([\d,]+\.\d{2})", text)
    if not sewer_match:
        raise ValueError(f"Could not find sewer volume charge in {pdf_path.name}")

    sewer_volume = float(sewer_match.group(1).replace(",", ""))

    # Calculate fixed costs (everything else)
    fixed_costs = round(total - water_volume - sewer_volume, 2)

    # Generate month key and label
    month_key = bill_date.strftime("%Y-%m")
    month_label = bill_date.strftime("%b %y")  # e.g., "Nov 24"

    return {
        "month": month_key,
        "label": month_label,
        "bill_date": bill_date.strftime("%Y-%m-%d"),
        "total": total,
        "ccf": ccf,
        "sewer_volume": sewer_volume,
        "water_volume": water_volume,
        "fixed_costs": fixed_costs,
        "source_file": pdf_path.name
    }


def load_existing_bills() -> list:
    """Load existing bills from JSON file."""
    if not OUTPUT_FILE.exists():
        return []
    with open(OUTPUT_FILE) as f:
        data = json.load(f)
    return data.get("bills", [])


def merge_bills(existing: list, new_entries: list) -> list:
    """
    Merge new entries into existing bills.

    Replaces entries with same month (for --rebuild case).
    Returns sorted list by month.
    """
    # Index existing by month
    by_month = {b["month"]: b for b in existing}

    # Add/replace with new entries
    for entry in new_entries:
        by_month[entry["month"]] = entry

    # Sort by month
    return sorted(by_month.values(), key=lambda b: b["month"])


def write_output(bills: list, dry_run: bool) -> None:
    """Write bills to JSON output file."""
    if dry_run:
        print("\n[Dry run] Would write to", OUTPUT_FILE)
        return

    output = {
        "bills": bills,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWritten {len(bills)} bills to {OUTPUT_FILE}")


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

    # Parse each new PDF
    new_entries = []
    for pdf in new_pdfs:
        print(f"\nParsing {pdf.name}...")
        try:
            entry = parse_water_bill(pdf)
            print(f"  Bill date: {entry['bill_date']}")
            print(f"  Total: ${entry['total']:,.2f}")
            print(f"  CCF: {entry['ccf']}")
            new_entries.append(entry)
        except ValueError as e:
            print(f"\nERROR: {e}")
            print("Parsing failed. Please check the PDF format.")
            sys.exit(1)

    print(f"\nSuccessfully parsed {len(new_entries)} bill(s)")

    # Load existing and merge
    existing_bills = load_existing_bills()
    all_bills = merge_bills(existing_bills, new_entries)

    # Write output
    write_output(all_bills, args.dry_run)

    # Update tracking file
    if not args.dry_run:
        for pdf in new_pdfs:
            processed.add(pdf.name)
        save_processed(processed)
        print(f"Updated tracking file: {len(processed)} PDFs processed")


if __name__ == "__main__":
    main()
