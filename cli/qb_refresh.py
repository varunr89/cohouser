#!/usr/bin/env python3
"""
QuickBooks Data Refresh CLI

Usage:
    python qb_refresh.py --fetch-tokens    Fetch tokens from Azure after OAuth
    python qb_refresh.py                   Refresh financial data
    python qb_refresh.py --dry-run         Fetch data but don't commit
    python qb_refresh.py --no-push         Commit but don't push
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from azure.storage.blob import BlobServiceClient

# Paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
DATA_DIR = SCRIPT_DIR.parent / "data"

# QuickBooks API base URL
QB_API_BASE = "https://quickbooks.api.intuit.com/v3/company"


def load_config() -> dict:
    """Load configuration from config.json."""
    if not CONFIG_PATH.exists():
        print(f"Error: {CONFIG_PATH} not found.")
        print(f"Copy config.example.json to config.json and fill in your credentials.")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """Save configuration to config.json."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Configuration saved to {CONFIG_PATH}")


def fetch_tokens_from_azure(config: dict) -> dict:
    """Fetch tokens from Azure Blob Storage after OAuth callback."""
    connection_string = config["azure_storage_connection_string"]
    realm_id = config["realm_id"]

    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client("qb-tokens")
    blob_client = container_client.get_blob_client(f"{realm_id}/tokens.json")

    try:
        blob_data = blob_client.download_blob().readall()
        tokens = json.loads(blob_data)
        print(f"Tokens fetched successfully for realm {realm_id}")
        return tokens
    except Exception as e:
        print(f"Error fetching tokens: {e}")
        print("Make sure Kelly has completed the OAuth authorization.")
        sys.exit(1)


def refresh_access_token(config: dict) -> dict:
    """Refresh the access token using the refresh token."""
    token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

    response = requests.post(
        token_endpoint,
        data={
            "grant_type": "refresh_token",
            "refresh_token": config["refresh_token"],
        },
        auth=(config["client_id"], config["client_secret"]),
        headers={"Accept": "application/json"},
    )

    if response.status_code != 200:
        print(f"Error refreshing token: {response.status_code}")
        print(response.text)
        print("\nRefresh token may have expired. Ask Kelly to re-authorize.")
        sys.exit(1)

    token_data = response.json()

    config["access_token"] = token_data["access_token"]
    config["refresh_token"] = token_data["refresh_token"]
    config["token_expiry"] = datetime.now(timezone.utc).isoformat()

    save_config(config)
    print("Access token refreshed successfully")
    return config


def ensure_valid_token(config: dict) -> dict:
    """Ensure we have a valid access token, refreshing if needed."""
    if not config.get("access_token") or not config.get("refresh_token"):
        print("No tokens found. Run with --fetch-tokens first.")
        sys.exit(1)

    # Always refresh to be safe (tokens only last 1 hour)
    return refresh_access_token(config)


def qb_api_request(config: dict, endpoint: str, params: dict = None) -> dict:
    """Make an authenticated request to the QuickBooks API."""
    url = f"{QB_API_BASE}/{config['realm_id']}/{endpoint}"

    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 401:
        print("Token expired, refreshing...")
        config = refresh_access_token(config)
        headers["Authorization"] = f"Bearer {config['access_token']}"
        response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"API Error {response.status_code}: {response.text}")
        sys.exit(1)

    return response.json()


def fetch_balance_sheet(config: dict) -> dict:
    """Fetch Balance Sheet report from QuickBooks."""
    print("Fetching Balance Sheet...")
    return qb_api_request(config, "reports/BalanceSheet")


def fetch_profit_and_loss(config: dict) -> dict:
    """Fetch Profit and Loss report from QuickBooks."""
    print("Fetching Profit and Loss...")
    return qb_api_request(config, "reports/ProfitAndLoss")


def fetch_transactions(config: dict, start_date: str, end_date: str) -> dict:
    """Fetch transactions (purchases and bills) from QuickBooks."""
    print("Fetching transactions...")

    # Fetch purchases
    purchases = qb_api_request(
        config,
        "query",
        params={"query": f"SELECT * FROM Purchase WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'"}
    )

    # Fetch bills
    bills = qb_api_request(
        config,
        "query",
        params={"query": f"SELECT * FROM Bill WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'"}
    )

    return {"purchases": purchases, "bills": bills}


# ============================================================================
# Balance Sheet Transformation
# ============================================================================

def parse_value(val: str) -> float:
    """Parse a currency string to float."""
    if not val:
        return 0.0
    try:
        return float(str(val).replace(",", ""))
    except ValueError:
        return 0.0


def find_section_by_group(rows: list, group: str) -> Optional[dict]:
    """Find a section by its group attribute."""
    for row in rows:
        if row.get("group") == group:
            return row
        # Recurse into nested rows
        nested = row.get("Rows", {}).get("Row", [])
        if nested:
            result = find_section_by_group(nested, group)
            if result:
                return result
    return None


def find_section_by_header(rows: list, header_contains: str) -> Optional[dict]:
    """Find a section by header text."""
    for row in rows:
        header = row.get("Header", {}).get("ColData", [{}])[0].get("value", "")
        if header_contains.lower() in header.lower():
            return row
        # Recurse into nested rows
        nested = row.get("Rows", {}).get("Row", [])
        if nested:
            result = find_section_by_header(nested, header_contains)
            if result:
                return result
    return None


def extract_accounts_from_section(section: dict) -> list:
    """Extract account data from a QB section."""
    accounts = []
    rows = section.get("Rows", {}).get("Row", [])

    for row in rows:
        if row.get("type") == "Data":
            col_data = row.get("ColData", [])
            if len(col_data) >= 2:
                name = col_data[0].get("value", "")
                balance = parse_value(col_data[1].get("value", "0"))
                if name and balance != 0:
                    accounts.append({
                        "label": name,
                        "current": balance,
                        "prior": 0,  # Would need prior period data
                        "change": 0
                    })
        elif row.get("type") == "Section":
            # Nested section - extract recursively
            header = row.get("Header", {}).get("ColData", [{}])[0].get("value", "")
            summary = row.get("Summary", {}).get("ColData", [])
            total = parse_value(summary[1].get("value", "0")) if len(summary) >= 2 else 0

            children = extract_accounts_from_section(row)

            if header and (total != 0 or children):
                accounts.append({
                    "label": header,
                    "current": total,
                    "prior": 0,
                    "change": 0,
                    "children": children if children else None
                })

    # Remove None children
    for acc in accounts:
        if "children" in acc and acc["children"] is None:
            del acc["children"]

    return accounts


def transform_balance_sheet(qb_data: dict) -> dict:
    """
    Transform QB Balance Sheet to dashboard format.

    Dashboard expects:
    {
        "bank": {
            "label": "Bank accounts (cash)",
            "subtitle": "...",
            "current": 190774,
            "prior": 185338,
            "change": 5436,
            "children": [...]
        },
        "investments": {...},
        "total": {...}
    }
    """
    rows = qb_data.get("Rows", {}).get("Row", [])

    # Find Bank Accounts section
    bank_section = find_section_by_group(rows, "BankAccounts")
    bank_accounts = []
    bank_total = 0

    if bank_section:
        bank_accounts = extract_accounts_from_section(bank_section)
        summary = bank_section.get("Summary", {}).get("ColData", [])
        bank_total = parse_value(summary[1].get("value", "0")) if len(summary) >= 2 else 0

    # Find Other Current Assets (investments)
    other_current_section = find_section_by_group(rows, "OtherCurrentAssets")
    investment_accounts = []
    investment_total = 0

    if other_current_section:
        investment_accounts = extract_accounts_from_section(other_current_section)
        summary = other_current_section.get("Summary", {}).get("ColData", [])
        investment_total = parse_value(summary[1].get("value", "0")) if len(summary) >= 2 else 0

    # Get total assets
    total_assets_section = find_section_by_group(rows, "TotalAssets")
    total_assets = 0
    if total_assets_section:
        summary = total_assets_section.get("Summary", {}).get("ColData", [])
        total_assets = parse_value(summary[1].get("value", "0")) if len(summary) >= 2 else 0

    # Calculate current assets total
    current_assets_total = bank_total + investment_total

    return {
        "bank": {
            "label": "Bank accounts (cash)",
            "subtitle": "Bank accounts and CDs held at WECU and First Federal.",
            "current": bank_total,
            "prior": 0,  # Would need prior period
            "change": 0,
            "children": bank_accounts
        },
        "investments": {
            "label": "Investments & CDs (other current assets)",
            "subtitle": "Other current assets including CDs and Vanguard funds.",
            "current": investment_total,
            "prior": 0,
            "change": 0,
            "children": investment_accounts
        },
        "total": {
            "label": "Total cash + investments",
            "subtitle": "Total current assets: bank accounts plus investments.",
            "current": current_assets_total,
            "prior": 0,
            "change": 0,
            "children": []  # Will reference bank and investments
        },
        "metadata": {
            "report_date": qb_data.get("Header", {}).get("EndPeriod", ""),
            "total_assets": total_assets
        }
    }


# ============================================================================
# Profit & Loss Transformation
# ============================================================================

def extract_expense_tree(section: dict) -> list:
    """Extract expense categories from a P&L section."""
    items = []
    rows = section.get("Rows", {}).get("Row", [])

    for row in rows:
        if row.get("type") == "Data":
            col_data = row.get("ColData", [])
            if len(col_data) >= 2:
                name = col_data[0].get("value", "")
                actual = abs(parse_value(col_data[1].get("value", "0")))
                if name:
                    items.append({
                        "label": name,
                        "actual": actual,
                        "budget": 0,  # Budget from separate source
                        "remaining": 0
                    })
        elif row.get("type") == "Section":
            header = row.get("Header", {}).get("ColData", [{}])[0].get("value", "")
            summary = row.get("Summary", {}).get("ColData", [])
            total = abs(parse_value(summary[1].get("value", "0"))) if len(summary) >= 2 else 0

            children = extract_expense_tree(row)

            if header:
                item = {
                    "label": header,
                    "actual": total,
                    "budget": 0,
                    "remaining": 0
                }
                if children:
                    item["children"] = children
                items.append(item)

    return items


def make_committee_key(name: str) -> str:
    """Convert a committee name to a camelCase key."""
    key = name.lower().replace(" ", "_").replace("-", "_")

    # Map to standard committee keys
    key_mapping = {
        "board": "board",
        "common_house": "commonHouse",
        "finance_committee": "finance",
        "landscape": "landscape",
        "maintenance": "maintenance",
        "meals": "meals",
        "utilities": "utilities",
        "community_building": "communityBuilding",
        "general_meetings": "generalMeetings",
        "tech_team": "techTeam",
    }

    for pattern, mapped_key in key_mapping.items():
        if pattern in key:
            return mapped_key

    return key


def process_committee_section(section: dict) -> dict:
    """Process a single committee section into dashboard format."""
    header = section.get("Header", {}).get("ColData", [{}])[0].get("value", "")
    summary = section.get("Summary", {}).get("ColData", [])
    total = abs(parse_value(summary[1].get("value", "0"))) if len(summary) >= 2 else 0

    children = extract_expense_tree(section)
    key = make_committee_key(header)

    return {
        "key": key,
        "name": header,
        "description": f"{header} expenses from QuickBooks.",
        "actual": total,
        "budget": 0,
        "remaining": 0,
        "children": children if children else []
    }


def transform_profit_and_loss(qb_data: dict) -> dict:
    """
    Transform QB P&L to dashboard committee format.

    Dashboard expects committees like board, commonHouse, finance, landscape,
    maintenance, meals, utilities - each with actual/budget/remaining and children.
    """
    rows = qb_data.get("Rows", {}).get("Row", [])

    # Find Expenses section
    expenses_section = None
    for row in rows:
        header = row.get("Header", {}).get("ColData", [{}])[0].get("value", "")
        if "Expense" in header:
            expenses_section = row
            break

    committees = {}

    if expenses_section:
        expense_rows = expenses_section.get("Rows", {}).get("Row", [])

        for row in expense_rows:
            if row.get("type") == "Section":
                header = row.get("Header", {}).get("ColData", [{}])[0].get("value", "")

                # Skip the generic "Expenses" wrapper if present
                if header == "Expenses":
                    # Process children of Expenses as committees
                    nested_rows = row.get("Rows", {}).get("Row", [])
                    for nested_row in nested_rows:
                        if nested_row.get("type") == "Section":
                            committee = process_committee_section(nested_row)
                            committees[committee["key"]] = committee
                else:
                    # This is a direct committee
                    committee = process_committee_section(row)
                    committees[committee["key"]] = committee

    return {
        "committees": committees,
        "metadata": {
            "start_period": qb_data.get("Header", {}).get("StartPeriod", ""),
            "end_period": qb_data.get("Header", {}).get("EndPeriod", "")
        }
    }


# ============================================================================
# Summary Generation
# ============================================================================

def create_summary(cash_data: dict, budget_data: dict) -> dict:
    """Create summary.json combining cash and budget data."""
    now = datetime.now()
    quarter = (now.month - 1) // 3 + 1

    # Cash totals
    bank_total = cash_data.get("bank", {}).get("current", 0)
    investment_total = cash_data.get("investments", {}).get("current", 0)

    # Budget totals
    total_actual = sum(c.get("actual", 0) for c in budget_data.get("committees", {}).values())

    committees_list = [
        {
            "name": data["name"],
            "actual": data["actual"],
            "budget": data["budget"],
            "remaining": data["remaining"],
            "percent": (data["actual"] / data["budget"] * 100) if data["budget"] > 0 else 0
        }
        for data in budget_data.get("committees", {}).values()
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": f"{now.year}-Q{quarter}",
        "report_date": cash_data.get("metadata", {}).get("report_date", ""),
        "cash_investments": {
            "bank_accounts": bank_total,
            "investments_cds": investment_total,
            "total": bank_total + investment_total,
            "change_from_prior": 0
        },
        "budget_vs_actual": {
            "total_budget": 0,
            "total_actual": total_actual,
            "total_remaining": 0,
            "percent_used": 0,
            "committees": committees_list
        }
    }


# ============================================================================
# File Writing and Git Operations
# ============================================================================

def write_json_file(path: Path, data: dict) -> None:
    """Write data to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Written: {path}")


def git_commit_and_push(dry_run: bool, no_push: bool) -> None:
    """Commit changes to git and optionally push."""
    if dry_run:
        print("\n[Dry run] Would commit and push changes")
        return

    try:
        # Stage data files
        subprocess.run(["git", "add", "data/"], check=True, cwd=SCRIPT_DIR.parent)

        # Check if there are changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=SCRIPT_DIR.parent
        )

        if result.returncode == 0:
            print("\nNo changes to commit")
            return

        # Commit
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"Update financial data {date_str}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True,
            cwd=SCRIPT_DIR.parent
        )
        print(f"\nCommitted: {commit_msg}")

        # Push
        if no_push:
            print("[No push] Changes committed locally only")
        else:
            subprocess.run(["git", "push"], check=True, cwd=SCRIPT_DIR.parent)
            print("Pushed to remote")

    except subprocess.CalledProcessError as e:
        print(f"\nGit error: {e}")
        print("Changes saved to data/ folder but not committed")
        sys.exit(1)


# ============================================================================
# Commands
# ============================================================================

def cmd_fetch_tokens(args):
    """Handle --fetch-tokens command."""
    config = load_config()

    if not config.get("realm_id"):
        print("Error: realm_id not set in config.json")
        print("Find your realm ID in the QuickBooks URL when logged in.")
        sys.exit(1)

    tokens = fetch_tokens_from_azure(config)

    config["access_token"] = tokens["access_token"]
    config["refresh_token"] = tokens["refresh_token"]
    config["token_expiry"] = tokens.get("created_at")

    save_config(config)
    print("\nTokens saved to config.json. You can now run: python qb_refresh.py")


def cmd_refresh_data(args):
    """Handle main data refresh command."""
    config = load_config()
    config = ensure_valid_token(config)

    # Fetch data from QuickBooks
    balance_sheet_raw = fetch_balance_sheet(config)
    profit_loss_raw = fetch_profit_and_loss(config)

    # Get date range for transactions (current year)
    year = datetime.now().year
    start_date = f"{year}-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    transactions_raw = fetch_transactions(config, start_date, end_date)

    # Transform data to dashboard format
    cash_data = transform_balance_sheet(balance_sheet_raw)
    budget_data = transform_profit_and_loss(profit_loss_raw)
    summary = create_summary(cash_data, budget_data)

    # Write JSON files in dashboard-compatible format
    write_json_file(DATA_DIR / "cash-investments.json", cash_data)
    write_json_file(DATA_DIR / "budget-vs-actual.json", budget_data)
    write_json_file(DATA_DIR / "summary.json", summary)

    # Store raw responses for debugging (gitignored)
    raw_dir = DATA_DIR / "raw"
    write_json_file(raw_dir / "balance-sheet-raw.json", balance_sheet_raw)
    write_json_file(raw_dir / "profit-loss-raw.json", profit_loss_raw)
    write_json_file(raw_dir / "transactions-raw.json", transactions_raw)

    print(f"\nData files written to {DATA_DIR}/")

    # Print summary
    print(f"\n--- Summary ---")
    print(f"Bank accounts: ${cash_data['bank']['current']:,.2f}")
    print(f"Investments:   ${cash_data['investments']['current']:,.2f}")
    print(f"Total:         ${cash_data['total']['current']:,.2f}")
    print(f"\nCommittees with expenses:")
    for key, committee in budget_data['committees'].items():
        print(f"  {committee['name']}: ${committee['actual']:,.2f}")

    # Git operations
    git_commit_and_push(args.dry_run, args.no_push)

    print("\nDone!")


def main():
    parser = argparse.ArgumentParser(description="QuickBooks Data Refresh CLI")
    parser.add_argument("--fetch-tokens", action="store_true",
                        help="Fetch tokens from Azure after OAuth")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch data but don't commit/push")
    parser.add_argument("--no-push", action="store_true",
                        help="Commit but don't push to remote")

    args = parser.parse_args()

    if args.fetch_tokens:
        cmd_fetch_tokens(args)
    else:
        cmd_refresh_data(args)


if __name__ == "__main__":
    main()
