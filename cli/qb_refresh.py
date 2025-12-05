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
    """Fetch Balance Sheet report from QuickBooks (current period)."""
    print("Fetching Balance Sheet (current)...")
    return qb_api_request(config, "reports/BalanceSheet")


def fetch_balance_sheet_prior(config: dict, as_of_date: str) -> dict:
    """Fetch Balance Sheet report for a specific prior date (start of year)."""
    print(f"Fetching Balance Sheet (as of {as_of_date})...")
    return qb_api_request(config, "reports/BalanceSheet", params={
        "date_macro": "",  # Clear the macro to use explicit date
        "start_date": as_of_date,
        "end_date": as_of_date
    })


def fetch_profit_and_loss(config: dict) -> dict:
    """Fetch Profit and Loss report from QuickBooks."""
    print("Fetching Profit and Loss...")
    return qb_api_request(config, "reports/ProfitAndLoss")


def fetch_budgets(config: dict) -> dict:
    """Fetch all Budget entities from QuickBooks."""
    print("Fetching Budgets...")
    try:
        result = qb_api_request(config, "query", params={
            "query": "SELECT * FROM Budget"
        })
        return result
    except Exception as e:
        print(f"Warning: Could not fetch budgets: {e}")
        return {"QueryResponse": {}}


def fetch_all_paginated(config: dict, base_query: str, entity_type: str) -> list:
    """Fetch all records with pagination for a given query."""
    all_records = []
    start_position = 1
    max_results = 1000

    while True:
        query = f"{base_query} STARTPOSITION {start_position} MAXRESULTS {max_results}"
        result = qb_api_request(config, "query", params={"query": query})

        records = result.get("QueryResponse", {}).get(entity_type, [])
        if not records:
            break

        all_records.extend(records)

        if len(records) < max_results:
            break

        start_position += len(records)

    return all_records


def fetch_transactions(config: dict, start_date: str, end_date: str) -> dict:
    """Fetch transactions (purchases, bills, and journal entries) from QuickBooks."""
    print("Fetching transactions...")

    # Fetch all purchases with pagination
    purchases = fetch_all_paginated(
        config,
        f"SELECT * FROM Purchase WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'",
        "Purchase"
    )
    print(f"  Fetched {len(purchases)} purchases")

    # Fetch all bills with pagination
    bills = fetch_all_paginated(
        config,
        f"SELECT * FROM Bill WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'",
        "Bill"
    )
    print(f"  Fetched {len(bills)} bills")

    # Fetch all journal entries with pagination (for accruals, prepaid expenses, etc.)
    journal_entries = fetch_all_paginated(
        config,
        f"SELECT * FROM JournalEntry WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'",
        "JournalEntry"
    )
    print(f"  Fetched {len(journal_entries)} journal entries")

    return {
        "purchases": {"QueryResponse": {"Purchase": purchases}},
        "bills": {"QueryResponse": {"Bill": bills}},
        "journal_entries": {"QueryResponse": {"JournalEntry": journal_entries}}
    }


def fetch_accounts(config: dict) -> dict:
    """Fetch Chart of Accounts from QuickBooks to get account hierarchy."""
    print("Fetching Chart of Accounts...")

    # QuickBooks API paginates at 100 records, so we need to fetch all pages
    all_accounts = []
    start_position = 1
    max_results = 1000  # Request larger batches

    while True:
        result = qb_api_request(
            config,
            "query",
            params={"query": f"SELECT * FROM Account STARTPOSITION {start_position} MAXRESULTS {max_results}"}
        )

        accounts = result.get("QueryResponse", {}).get("Account", [])
        if not accounts:
            break

        all_accounts.extend(accounts)

        # If we got fewer than max_results, we've reached the end
        if len(accounts) < max_results:
            break

        start_position += len(accounts)

    return {"QueryResponse": {"Account": all_accounts}}


def build_account_mapping(accounts_data: dict) -> dict:
    """
    Build a mapping from account ID and name to full hierarchical path.

    Returns dict with two sub-dicts:
    - by_id: {account_id: full_path}
    - by_name: {leaf_name: full_path}  (for accounts without ID in transactions)
    """
    accounts = accounts_data.get("QueryResponse", {}).get("Account", [])

    # First pass: build id -> account info
    id_to_account = {}
    for acct in accounts:
        acct_id = acct.get("Id")
        id_to_account[acct_id] = {
            "name": acct.get("Name", ""),
            "parent_id": acct.get("ParentRef", {}).get("value"),
            "full_name": acct.get("FullyQualifiedName", acct.get("Name", "")),
            "type": acct.get("AccountType", ""),
            "subtype": acct.get("AccountSubType", ""),
        }

    # Build mappings
    by_id = {}
    by_name = {}

    for acct_id, info in id_to_account.items():
        full_name = info["full_name"]
        leaf_name = info["name"]

        by_id[acct_id] = full_name

        # Only map leaf names for expense/utility accounts to avoid collisions
        if "Expense" in info["type"] or "Utilities" in full_name:
            if leaf_name not in by_name:
                by_name[leaf_name] = full_name

    return {"by_id": by_id, "by_name": by_name}


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


def extract_accounts_flat(section: dict, prefix: str = "") -> dict:
    """
    Extract accounts from a section as a flat dict: {account_name: balance}.
    Used for prior period lookup.
    """
    accounts = {}
    rows = section.get("Rows", {}).get("Row", [])

    for row in rows:
        if row.get("type") == "Data":
            col_data = row.get("ColData", [])
            if len(col_data) >= 2:
                name = col_data[0].get("value", "")
                balance = parse_value(col_data[1].get("value", "0"))
                if name:
                    full_name = f"{prefix}:{name}" if prefix else name
                    accounts[name] = balance  # Use short name for lookup
        elif row.get("type") == "Section":
            header = row.get("Header", {}).get("ColData", [{}])[0].get("value", "")
            summary = row.get("Summary", {}).get("ColData", [])
            total = parse_value(summary[1].get("value", "0")) if len(summary) >= 2 else 0

            if header:
                accounts[header] = total
                # Recurse into children
                child_prefix = f"{prefix}:{header}" if prefix else header
                child_accounts = extract_accounts_flat(row, child_prefix)
                accounts.update(child_accounts)

    return accounts


def extract_accounts_from_section(section: dict, prior_lookup: dict = None) -> list:
    """Extract account data from a QB section with optional prior period data."""
    if prior_lookup is None:
        prior_lookup = {}

    accounts = []
    rows = section.get("Rows", {}).get("Row", [])

    for row in rows:
        if row.get("type") == "Data":
            col_data = row.get("ColData", [])
            if len(col_data) >= 2:
                name = col_data[0].get("value", "")
                balance = parse_value(col_data[1].get("value", "0"))
                if name and balance != 0:
                    prior = prior_lookup.get(name, 0)
                    accounts.append({
                        "label": name,
                        "current": balance,
                        "prior": prior,
                        "change": round(balance - prior, 2)
                    })
        elif row.get("type") == "Section":
            # Nested section - extract recursively
            header = row.get("Header", {}).get("ColData", [{}])[0].get("value", "")
            summary = row.get("Summary", {}).get("ColData", [])
            total = parse_value(summary[1].get("value", "0")) if len(summary) >= 2 else 0

            children = extract_accounts_from_section(row, prior_lookup)
            prior = prior_lookup.get(header, 0)

            if header and (total != 0 or children):
                accounts.append({
                    "label": header,
                    "current": total,
                    "prior": prior,
                    "change": round(total - prior, 2),
                    "children": children if children else None
                })

    # Remove None children
    for acc in accounts:
        if "children" in acc and acc["children"] is None:
            del acc["children"]

    return accounts


def extract_section_totals(qb_data: dict) -> dict:
    """Extract bank and investment totals from a balance sheet."""
    rows = qb_data.get("Rows", {}).get("Row", [])

    bank_section = find_section_by_group(rows, "BankAccounts")
    bank_total = 0
    if bank_section:
        summary = bank_section.get("Summary", {}).get("ColData", [])
        bank_total = parse_value(summary[1].get("value", "0")) if len(summary) >= 2 else 0

    other_current_section = find_section_by_group(rows, "OtherCurrentAssets")
    investment_total = 0
    if other_current_section:
        summary = other_current_section.get("Summary", {}).get("ColData", [])
        investment_total = parse_value(summary[1].get("value", "0")) if len(summary) >= 2 else 0

    return {
        "bank": bank_total,
        "investments": investment_total,
        "total": bank_total + investment_total
    }


def transform_balance_sheet(qb_data: dict, prior_data: dict = None) -> dict:
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

    Args:
        qb_data: Current period balance sheet from QB API
        prior_data: Optional prior period balance sheet (e.g., start of year)
    """
    rows = qb_data.get("Rows", {}).get("Row", [])

    # Extract prior period account-level data if available
    prior_totals = {"bank": 0, "investments": 0, "total": 0}
    prior_bank_lookup = {}
    prior_investment_lookup = {}
    prior_date = None

    if prior_data:
        prior_rows = prior_data.get("Rows", {}).get("Row", [])
        prior_totals = extract_section_totals(prior_data)
        prior_date = prior_data.get("Header", {}).get("EndPeriod", "")

        # Extract account-level prior values for bank accounts
        prior_bank_section = find_section_by_group(prior_rows, "BankAccounts")
        if prior_bank_section:
            prior_bank_lookup = extract_accounts_flat(prior_bank_section)

        # Extract account-level prior values for investments
        prior_investment_section = find_section_by_group(prior_rows, "OtherCurrentAssets")
        if prior_investment_section:
            prior_investment_lookup = extract_accounts_flat(prior_investment_section)

    # Find Bank Accounts section
    bank_section = find_section_by_group(rows, "BankAccounts")
    bank_accounts = []
    bank_total = 0

    if bank_section:
        bank_accounts = extract_accounts_from_section(bank_section, prior_bank_lookup)
        summary = bank_section.get("Summary", {}).get("ColData", [])
        bank_total = parse_value(summary[1].get("value", "0")) if len(summary) >= 2 else 0

    # Find Other Current Assets (investments)
    other_current_section = find_section_by_group(rows, "OtherCurrentAssets")
    investment_accounts = []
    investment_total = 0

    if other_current_section:
        investment_accounts = extract_accounts_from_section(other_current_section, prior_investment_lookup)
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
            "prior": prior_totals["bank"],
            "change": round(bank_total - prior_totals["bank"], 2),
            "children": bank_accounts
        },
        "investments": {
            "label": "Investments & CDs (other current assets)",
            "subtitle": "Other current assets including CDs and Vanguard funds.",
            "current": investment_total,
            "prior": prior_totals["investments"],
            "change": round(investment_total - prior_totals["investments"], 2),
            "children": investment_accounts
        },
        "total": {
            "label": "Total cash + investments",
            "subtitle": "Total current assets: bank accounts plus investments.",
            "current": current_assets_total,
            "prior": prior_totals["total"],
            "change": round(current_assets_total - prior_totals["total"], 2),
            "children": []
        },
        "metadata": {
            "report_date": qb_data.get("Header", {}).get("EndPeriod", ""),
            "prior_date": prior_date,
            "total_assets": total_assets
        }
    }


# ============================================================================
# Profit & Loss Transformation
# ============================================================================

def extract_expense_tree(section: dict, budgets: dict = None, path_prefix: str = "") -> list:
    """
    Extract expense categories from a P&L section with budget matching.

    Args:
        section: QB P&L section data
        budgets: Dict of {full_account_path: amount} for budget lookup
        path_prefix: Current path in the expense hierarchy (e.g., "Expenses:Board")
    """
    if budgets is None:
        budgets = {}

    items = []
    rows = section.get("Rows", {}).get("Row", [])

    for row in rows:
        if row.get("type") == "Data":
            col_data = row.get("ColData", [])
            if len(col_data) >= 2:
                name = col_data[0].get("value", "")
                actual = abs(parse_value(col_data[1].get("value", "0")))
                if name:
                    # Build full path for budget lookup
                    full_path = f"{path_prefix}:{name}" if path_prefix else name
                    budget = budgets.get(full_path, 0)
                    items.append({
                        "label": name,
                        "actual": actual,
                        "budget": budget,
                        "remaining": max(0, budget - actual) if budget > 0 else 0
                    })
        elif row.get("type") == "Section":
            header = row.get("Header", {}).get("ColData", [{}])[0].get("value", "")
            summary = row.get("Summary", {}).get("ColData", [])
            total = abs(parse_value(summary[1].get("value", "0"))) if len(summary) >= 2 else 0

            # Build path for children
            child_path = f"{path_prefix}:{header}" if path_prefix else header
            children = extract_expense_tree(row, budgets, child_path)

            # Get budget for this section (sum of children or direct match)
            full_path = f"{path_prefix}:{header}" if path_prefix else header
            budget = budgets.get(full_path, 0)

            # If no direct budget, sum children budgets
            if budget == 0 and children:
                budget = sum(c.get("budget", 0) for c in children)

            if header:
                item = {
                    "label": header,
                    "actual": total,
                    "budget": budget,
                    "remaining": max(0, budget - total) if budget > 0 else 0
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


def process_committee_section(section: dict, budgets: dict = None, parent_path: str = "Expenses") -> dict:
    """
    Process a single committee section into dashboard format.

    Args:
        section: QB P&L section data
        budgets: Dict of {full_account_path: amount} for budget lookup
        parent_path: Parent path for building full account paths (usually "Expenses" or "Utilities")
    """
    if budgets is None:
        budgets = {}

    header = section.get("Header", {}).get("ColData", [{}])[0].get("value", "")
    summary = section.get("Summary", {}).get("ColData", [])
    total = abs(parse_value(summary[1].get("value", "0"))) if len(summary) >= 2 else 0

    # Build path for this committee's children
    # For Utilities, paths are "Utilities:Electricity" not "Utilities:Utilities:Electricity"
    if parent_path == header:
        # Parent path IS the header (e.g., Utilities section under Utilities parent)
        committee_path = header
    else:
        committee_path = f"{parent_path}:{header}"

    children = extract_expense_tree(section, budgets, committee_path)
    key = make_committee_key(header)

    return {
        "key": key,
        "name": header,
        "description": f"{header} expenses from QuickBooks.",
        "actual": total,
        "budget": 0,  # Committee-level budget set by transform_profit_and_loss
        "remaining": 0,
        "children": children if children else []
    }


def parse_budgets(budget_response: dict) -> dict:
    """
    Parse QuickBooks Budget entity response into a lookup by account name.

    Returns dict like: {"Utilities": 77850, "Board": 10927, ...}
    """
    budgets_by_account = {}

    # Get budgets from QueryResponse
    budgets = budget_response.get("QueryResponse", {}).get("Budget", [])

    if not budgets:
        print("No budgets found in QuickBooks")
        return budgets_by_account

    # Find the current year's P&L budget
    current_year = datetime.now().year
    target_budget = None

    for budget in budgets:
        budget_type = budget.get("BudgetType", "")
        start_date = budget.get("StartDate", "")

        # Look for P&L budget for current year
        if budget_type == "ProfitAndLoss" and str(current_year) in start_date:
            target_budget = budget
            print(f"Found budget: {budget.get('Name', 'Unnamed')} ({start_date})")
            break

    if not target_budget:
        # Try any P&L budget
        for budget in budgets:
            if budget.get("BudgetType") == "ProfitAndLoss":
                target_budget = budget
                print(f"Using budget: {budget.get('Name', 'Unnamed')}")
                break

    if not target_budget:
        print("No P&L budget found")
        return budgets_by_account

    # Extract budget details by account
    # QuickBooks uses AccountRef (not Account) for budget line items
    for detail in target_budget.get("BudgetDetail", []):
        account_ref = detail.get("AccountRef", {})
        account_name = account_ref.get("name", "")
        amount = detail.get("Amount", 0)

        if account_name and amount:
            # Accumulate amounts for the same account (monthly entries sum to annual)
            budgets_by_account[account_name] = budgets_by_account.get(account_name, 0) + float(amount)

    print(f"Parsed {len(budgets_by_account)} budget accounts")
    return budgets_by_account


def match_budget_to_committee(committee_name: str, budgets: dict) -> float:
    """
    Match a committee name to budget amounts.

    Budget accounts are hierarchical like "Expenses:Board:Tech Team:Internet access"
    Committee names are top-level like "Board", "Common House", etc.
    We need to sum all budget entries that belong to a committee.
    """
    total = 0
    name_lower = committee_name.lower()

    # Map committee names to their budget path prefixes
    committee_prefixes = {
        "board": ["Expenses:Board"],
        "common house": ["Expenses:Common House"],
        "finance committee": ["Expenses:Finance Committee"],
        "finance": ["Expenses:Finance Committee"],
        "landscape": ["Expenses:Landscape"],
        "maintenance": ["Expenses:Maintenance"],
        "meals": ["Expenses:Meals"],
        "utilities": ["Utilities:"],  # Utilities are at top level, not under Expenses
    }

    # Find the matching prefixes for this committee
    prefixes = committee_prefixes.get(name_lower, [])

    if not prefixes:
        # Try fuzzy match on committee name
        for key, val in committee_prefixes.items():
            if key in name_lower or name_lower in key:
                prefixes = val
                break

    # Sum all budget entries that match the prefixes
    for budget_name, amount in budgets.items():
        for prefix in prefixes:
            if budget_name.startswith(prefix):
                total += amount
                break

    return total


def transform_profit_and_loss(qb_data: dict, budgets: dict = None) -> dict:
    """
    Transform QB P&L to dashboard committee format.

    Dashboard expects committees like board, commonHouse, finance, landscape,
    maintenance, meals, utilities - each with actual/budget/remaining and children.

    Args:
        qb_data: P&L report from QuickBooks
        budgets: Optional dict of budget amounts by account name
    """
    if budgets is None:
        budgets = {}

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
                            committee = process_committee_section(nested_row, budgets, "Expenses")
                            # Apply committee-level budget
                            budget_amount = match_budget_to_committee(committee["name"], budgets)
                            committee["budget"] = budget_amount
                            committee["remaining"] = max(0, budget_amount - committee["actual"])
                            committees[committee["key"]] = committee
                else:
                    # This is a direct committee (e.g., Utilities at top level)
                    # Utilities paths start with "Utilities:" not "Expenses:"
                    parent_path = header if header == "Utilities" else "Expenses"
                    committee = process_committee_section(row, budgets, parent_path)
                    # Apply committee-level budget
                    budget_amount = match_budget_to_committee(committee["name"], budgets)
                    committee["budget"] = budget_amount
                    committee["remaining"] = max(0, budget_amount - committee["actual"])
                    committees[committee["key"]] = committee

    return {
        "committees": committees,
        "metadata": {
            "start_period": qb_data.get("Header", {}).get("StartPeriod", ""),
            "end_period": qb_data.get("Header", {}).get("EndPeriod", ""),
            "budgets_loaded": len(budgets) > 0
        }
    }


# ============================================================================
# Transaction Transformation
# ============================================================================

def transform_transactions(raw_data: dict, account_mapping: dict = None) -> dict:
    """
    Transform raw QuickBooks purchase data into a flat transaction list.

    Args:
        raw_data: Raw transaction data from QuickBooks
        account_mapping: Dict with 'by_id' and 'by_name' mappings to full account paths

    Maps each transaction's account path to its committee.
    """
    transactions = []
    account_mapping = account_mapping or {"by_id": {}, "by_name": {}}

    # Map account path prefixes to committee keys
    committee_mapping = {
        "Expenses:Board": "Board",
        "Expenses:Common House": "Common House",
        "Expenses:Finance Committee": "Finance Committee",
        "Expenses:Landscape": "Landscape",
        "Expenses:Maintenance": "Maintenance",
        "Expenses:Meals": "Meals",
        "Utilities": "Utilities",
    }

    def get_committee(account_path: str) -> str:
        """Extract committee from full account path."""
        for prefix, committee in committee_mapping.items():
            if account_path.startswith(prefix):
                return committee
        return "Other"

    def get_line_item(account_path: str) -> str:
        """Extract the leaf account name from full path."""
        parts = account_path.split(":")
        return parts[-1] if parts else account_path

    def resolve_account_path(account_ref: dict) -> str:
        """Resolve account reference to full hierarchical path."""
        acct_id = account_ref.get("value", "")
        acct_name = account_ref.get("name", "")

        # Try by ID first (most reliable)
        if acct_id and acct_id in account_mapping["by_id"]:
            return account_mapping["by_id"][acct_id]

        # Fall back to name lookup
        if acct_name and acct_name in account_mapping["by_name"]:
            return account_mapping["by_name"][acct_name]

        # Last resort: return the name as-is (won't match committee)
        return acct_name

    def is_expense_account(account_path: str) -> bool:
        """Check if account path is an expense account we want to include."""
        return account_path.startswith("Expenses:") or account_path.startswith("Utilities")

    # Process purchases (checks, credit card charges, etc.)
    purchases = raw_data.get("purchases", {}).get("QueryResponse", {}).get("Purchase", [])

    for purchase in purchases:
        vendor = purchase.get("EntityRef", {}).get("name", "") or ""
        date = purchase.get("TxnDate", "")

        # Each purchase can have multiple line items
        for line in purchase.get("Line", []):
            detail = line.get("AccountBasedExpenseLineDetail", {})
            account_ref = detail.get("AccountRef", {})

            if not account_ref:
                continue

            # Resolve to full path using the account mapping
            account_path = resolve_account_path(account_ref)

            if not account_path or not is_expense_account(account_path):
                continue

            amount = line.get("Amount", 0)
            memo = line.get("Description", "") or ""

            transactions.append({
                "date": date,
                "vendor": vendor,
                "account": get_line_item(account_path),
                "accountPath": account_path,
                "committee": get_committee(account_path),
                "amount": amount,
                "memo": memo,
                "type": "Purchase",
            })

    # Process journal entries (for accruals, prepaid expenses, adjustments)
    journal_entries = raw_data.get("journal_entries", {}).get("QueryResponse", {}).get("JournalEntry", [])

    for entry in journal_entries:
        date = entry.get("TxnDate", "")
        doc_number = entry.get("DocNumber", "")

        for line in entry.get("Line", []):
            detail = line.get("JournalEntryLineDetail", {})
            account_ref = detail.get("AccountRef", {})
            posting_type = detail.get("PostingType", "")

            # Only include debit entries to expense accounts (debits increase expenses)
            if posting_type != "Debit":
                continue

            if not account_ref:
                continue

            account_path = resolve_account_path(account_ref)

            if not account_path or not is_expense_account(account_path):
                continue

            amount = line.get("Amount", 0)
            description = line.get("Description", "") or ""

            transactions.append({
                "date": date,
                "vendor": f"Journal Entry {doc_number}" if doc_number else "Journal Entry",
                "account": get_line_item(account_path),
                "accountPath": account_path,
                "committee": get_committee(account_path),
                "amount": amount,
                "memo": description,
                "type": "JournalEntry",
            })

    # Sort by date descending (newest first)
    transactions.sort(key=lambda t: t["date"], reverse=True)

    return {
        "transactions": transactions,
        "metadata": {
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "transaction_count": len(transactions),
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

    # Get date range for current year
    year = datetime.now().year
    start_of_year = f"{year}-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch data from QuickBooks
    balance_sheet_raw = fetch_balance_sheet(config)
    profit_loss_raw = fetch_profit_and_loss(config)

    # Fetch prior period (start of year) balance sheet for YTD comparison
    print("Fetching start-of-year balance sheet for comparison...")
    try:
        balance_sheet_prior = fetch_balance_sheet_prior(config, start_of_year)
    except Exception as e:
        print(f"Warning: Could not fetch prior period data: {e}")
        balance_sheet_prior = None

    # Fetch budgets from QuickBooks
    budget_raw = fetch_budgets(config)
    budgets = parse_budgets(budget_raw)

    transactions_raw = fetch_transactions(config, start_of_year, end_date)

    # Fetch Chart of Accounts for account hierarchy mapping
    accounts_raw = fetch_accounts(config)
    account_mapping = build_account_mapping(accounts_raw)

    # Transform data to dashboard format (with prior period and budget data)
    cash_data = transform_balance_sheet(balance_sheet_raw, balance_sheet_prior)
    budget_data = transform_profit_and_loss(profit_loss_raw, budgets)
    summary = create_summary(cash_data, budget_data)

    # Transform and write transactions (with account mapping for hierarchy)
    transactions_data = transform_transactions(transactions_raw, account_mapping)
    write_json_file(DATA_DIR / "transactions.json", transactions_data)

    # Write JSON files in dashboard-compatible format
    write_json_file(DATA_DIR / "cash-investments.json", cash_data)
    write_json_file(DATA_DIR / "budget-vs-actual.json", budget_data)
    write_json_file(DATA_DIR / "summary.json", summary)

    # Store raw responses for debugging (gitignored)
    raw_dir = DATA_DIR / "raw"
    write_json_file(raw_dir / "balance-sheet-raw.json", balance_sheet_raw)
    write_json_file(raw_dir / "profit-loss-raw.json", profit_loss_raw)
    write_json_file(raw_dir / "transactions-raw.json", transactions_raw)
    write_json_file(raw_dir / "budgets-raw.json", budget_raw)
    write_json_file(raw_dir / "accounts-raw.json", accounts_raw)
    if balance_sheet_prior:
        write_json_file(raw_dir / "balance-sheet-prior-raw.json", balance_sheet_prior)

    print(f"\nData files written to {DATA_DIR}/")

    # Print summary
    print(f"\n--- Cash Summary ---")
    print(f"Bank accounts: ${cash_data['bank']['current']:,.2f}")
    if cash_data['bank']['prior']:
        print(f"  (Jan 1: ${cash_data['bank']['prior']:,.2f}, Change: ${cash_data['bank']['change']:,.2f})")
    print(f"Investments:   ${cash_data['investments']['current']:,.2f}")
    if cash_data['investments']['prior']:
        print(f"  (Jan 1: ${cash_data['investments']['prior']:,.2f}, Change: ${cash_data['investments']['change']:,.2f})")
    print(f"Total:         ${cash_data['total']['current']:,.2f}")

    print(f"\n--- Budget vs Actual ---")
    budgets_found = budget_data.get('metadata', {}).get('budgets_loaded', False)
    if budgets_found:
        print("(Budgets loaded from QuickBooks)")
    else:
        print("(No budgets found in QuickBooks - showing actuals only)")

    for key, committee in budget_data['committees'].items():
        budget_amt = committee.get('budget', 0)
        actual_amt = committee.get('actual', 0)
        if budget_amt > 0:
            pct = (actual_amt / budget_amt) * 100
            print(f"  {committee['name']}: ${actual_amt:,.2f} / ${budget_amt:,.2f} ({pct:.0f}%)")
        else:
            print(f"  {committee['name']}: ${actual_amt:,.2f} (no budget)")

    print(f"\n--- Transactions ---")
    print(f"Total expense transactions: {transactions_data['metadata']['transaction_count']}")

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
