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


def transform_balance_sheet(qb_data: dict) -> dict:
    """Transform QB Balance Sheet to our schema."""
    accounts = []

    # Navigate QB report structure
    rows = qb_data.get("Rows", {}).get("Row", [])

    for section in rows:
        section_name = section.get("Header", {}).get("ColData", [{}])[0].get("value", "")

        # Look for Assets section
        if "Asset" in section_name:
            extract_accounts_recursive(section, accounts)

    return {"accounts": accounts, "raw_sections": rows}


def extract_accounts_recursive(section: dict, accounts: list, depth: int = 0) -> None:
    """Recursively extract accounts from nested QB report structure."""
    rows = section.get("Rows", {}).get("Row", [])

    for row in rows:
        if row.get("type") == "Data":
            account = extract_account_from_row(row)
            if account:
                accounts.append(account)
        elif row.get("type") == "Section":
            extract_accounts_recursive(row, accounts, depth + 1)


def extract_account_from_row(row: dict) -> dict | None:
    """Extract account info from a QB report row."""
    if row.get("type") == "Data":
        col_data = row.get("ColData", [])
        if len(col_data) >= 2:
            name = col_data[0].get("value", "")
            balance = col_data[1].get("value", "0")
            try:
                balance = float(str(balance).replace(",", ""))
            except ValueError:
                balance = 0.0

            # Determine account type from name
            account_type = "bank"
            if "CD" in name or "Certificate" in name:
                account_type = "cd"
            elif "Vanguard" in name or "Investment" in name:
                account_type = "investment"

            return {
                "name": name,
                "type": account_type,
                "balance": balance
            }
    return None


def transform_profit_and_loss(qb_data: dict) -> dict:
    """Transform QB P&L to our budget vs actual schema."""
    committees = {}

    rows = qb_data.get("Rows", {}).get("Row", [])

    for section in rows:
        header = section.get("Header", {}).get("ColData", [{}])[0].get("value", "")

        # Extract expense categories (committees)
        if "Expense" in header:
            extract_committees_recursive(section, committees)

    return {"committees": committees, "raw_sections": rows}


def extract_committees_recursive(section: dict, committees: dict) -> None:
    """Recursively extract committee/expense info from QB P&L."""
    rows = section.get("Rows", {}).get("Row", [])

    for row in rows:
        if row.get("type") == "Section":
            header = row.get("Header", {}).get("ColData", [])
            if header:
                name = header[0].get("value", "")
                if name:
                    # Get actual amount from summary
                    summary = row.get("Summary", {}).get("ColData", [])
                    actual = 0.0
                    if len(summary) >= 2:
                        try:
                            actual = float(str(summary[1].get("value", "0")).replace(",", ""))
                        except ValueError:
                            pass

                    committees[name] = {
                        "name": name,
                        "budget": 0,  # Budget comes from separate source
                        "actual": abs(actual),
                        "categories": []
                    }
            # Continue recursing
            extract_committees_recursive(row, committees)


def create_summary(balance_sheet: dict, budget_vs_actual: dict) -> dict:
    """Create summary.json from transformed data."""
    # Calculate totals from balance sheet
    bank_total = sum(a["balance"] for a in balance_sheet["accounts"] if a["type"] == "bank")
    investment_total = sum(a["balance"] for a in balance_sheet["accounts"] if a["type"] in ["cd", "investment"])

    # Calculate budget totals
    total_actual = sum(c["actual"] for c in budget_vs_actual["committees"].values())

    # Get current quarter
    now = datetime.now()
    quarter = (now.month - 1) // 3 + 1

    committees_list = [
        {
            "name": name,
            "budget": data["budget"],
            "actual": data["actual"],
            "percent": (data["actual"] / data["budget"] * 100) if data["budget"] > 0 else 0
        }
        for name, data in budget_vs_actual["committees"].items()
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": f"{now.year}-Q{quarter}",
        "cash_investments": {
            "bank_accounts": bank_total,
            "investments_cds": investment_total,
            "total": bank_total + investment_total,
            "change_from_prior": 0  # Would need historical data
        },
        "budget_vs_actual": {
            "total_budget": 0,  # Would need budget data
            "total_actual": total_actual,
            "total_remaining": 0,
            "percent_used": 0,
            "committees": committees_list
        }
    }


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

    # Transform data
    balance_sheet = transform_balance_sheet(balance_sheet_raw)
    budget_vs_actual = transform_profit_and_loss(profit_loss_raw)
    summary = create_summary(balance_sheet, budget_vs_actual)

    # Write JSON files
    write_json_file(DATA_DIR / "summary.json", summary)
    write_json_file(DATA_DIR / "balance-sheet.json", balance_sheet)
    write_json_file(DATA_DIR / "budget-vs-actual.json", budget_vs_actual)

    # Store raw responses for debugging (gitignored)
    raw_dir = DATA_DIR / "raw"
    write_json_file(raw_dir / "balance-sheet-raw.json", balance_sheet_raw)
    write_json_file(raw_dir / "profit-loss-raw.json", profit_loss_raw)
    write_json_file(raw_dir / "transactions-raw.json", transactions_raw)

    print(f"\nData files written to {DATA_DIR}/")

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
