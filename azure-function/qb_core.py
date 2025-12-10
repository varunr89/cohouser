"""
QuickBooks API and Data Transformation Core Module

This module provides reusable functions for fetching and transforming QuickBooks data.
All functions are self-contained with no file I/O - data is passed as parameters and
returned as dictionaries.

Used by:
- CLI tool (cli/qb_refresh.py)
- Azure Function (azure-function/function_app.py)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import requests

# QuickBooks API base URL
QB_API_BASE = "https://quickbooks.api.intuit.com/v3/company"


# ============================================================================
# Token Management
# ============================================================================

def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """
    Refresh the access token using the refresh token.

    Args:
        client_id: QuickBooks OAuth client ID
        client_secret: QuickBooks OAuth client secret
        refresh_token: Current refresh token

    Returns:
        Dict with 'access_token' and 'refresh_token' keys

    Raises:
        requests.HTTPError: If token refresh fails
    """
    token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

    response = requests.post(
        token_endpoint,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=(client_id, client_secret),
        headers={"Accept": "application/json"},
    )

    if response.status_code != 200:
        raise requests.HTTPError(
            f"Token refresh failed: {response.status_code} - {response.text}"
        )

    token_data = response.json()
    return {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
    }


# ============================================================================
# QuickBooks API Requests
# ============================================================================

def qb_api_request(access_token: str, realm_id: str, endpoint: str, params: dict = None) -> dict:
    """
    Make an authenticated request to the QuickBooks API.

    Args:
        access_token: QuickBooks OAuth access token
        realm_id: QuickBooks company/realm ID
        endpoint: API endpoint (e.g., 'reports/BalanceSheet')
        params: Optional query parameters

    Returns:
        JSON response as dict

    Raises:
        requests.HTTPError: If API request fails
    """
    url = f"{QB_API_BASE}/{realm_id}/{endpoint}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise requests.HTTPError(
            f"QuickBooks API error {response.status_code}: {response.text}"
        )

    return response.json()


def fetch_all_paginated(access_token: str, realm_id: str, base_query: str, entity_type: str) -> list:
    """
    Fetch all records with pagination for a given query.

    Args:
        access_token: QuickBooks OAuth access token
        realm_id: QuickBooks company/realm ID
        base_query: Base SQL-like query (e.g., "SELECT * FROM Purchase WHERE...")
        entity_type: Entity type in response (e.g., "Purchase", "Account")

    Returns:
        List of all records
    """
    all_records = []
    start_position = 1
    max_results = 1000

    while True:
        query = f"{base_query} STARTPOSITION {start_position} MAXRESULTS {max_results}"
        result = qb_api_request(access_token, realm_id, "query", params={"query": query})

        records = result.get("QueryResponse", {}).get(entity_type, [])
        if not records:
            break

        all_records.extend(records)

        if len(records) < max_results:
            break

        start_position += len(records)

    return all_records


# ============================================================================
# Data Fetching Functions
# ============================================================================

def fetch_balance_sheet(access_token: str, realm_id: str) -> dict:
    """
    Fetch Balance Sheet report from QuickBooks (current period).

    Args:
        access_token: QuickBooks OAuth access token
        realm_id: QuickBooks company/realm ID

    Returns:
        Balance sheet report data as dict
    """
    return qb_api_request(access_token, realm_id, "reports/BalanceSheet")


def fetch_balance_sheet_prior(access_token: str, realm_id: str, as_of_date: str) -> dict:
    """
    Fetch Balance Sheet report for a specific prior date.

    Args:
        access_token: QuickBooks OAuth access token
        realm_id: QuickBooks company/realm ID
        as_of_date: Date string in YYYY-MM-DD format

    Returns:
        Balance sheet report data as dict
    """
    return qb_api_request(access_token, realm_id, "reports/BalanceSheet", params={
        "date_macro": "",  # Clear the macro to use explicit date
        "start_date": as_of_date,
        "end_date": as_of_date
    })


def fetch_profit_and_loss(access_token: str, realm_id: str) -> dict:
    """
    Fetch Profit and Loss report from QuickBooks.

    Args:
        access_token: QuickBooks OAuth access token
        realm_id: QuickBooks company/realm ID

    Returns:
        P&L report data as dict
    """
    return qb_api_request(access_token, realm_id, "reports/ProfitAndLoss")


def fetch_budgets(access_token: str, realm_id: str) -> dict:
    """
    Fetch all Budget entities from QuickBooks.

    Args:
        access_token: QuickBooks OAuth access token
        realm_id: QuickBooks company/realm ID

    Returns:
        Budget query response as dict, or empty response if budgets unavailable
    """
    try:
        result = qb_api_request(access_token, realm_id, "query", params={
            "query": "SELECT * FROM Budget"
        })
        return result
    except Exception:
        return {"QueryResponse": {}}


def fetch_transactions(access_token: str, realm_id: str, start_date: str, end_date: str) -> dict:
    """
    Fetch transactions (purchases, bills, and journal entries) from QuickBooks.

    Args:
        access_token: QuickBooks OAuth access token
        realm_id: QuickBooks company/realm ID
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Dict with 'purchases', 'bills', and 'journal_entries' keys
    """
    # Fetch all purchases with pagination
    purchases = fetch_all_paginated(
        access_token,
        realm_id,
        f"SELECT * FROM Purchase WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'",
        "Purchase"
    )

    # Fetch all bills with pagination
    bills = fetch_all_paginated(
        access_token,
        realm_id,
        f"SELECT * FROM Bill WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'",
        "Bill"
    )

    # Fetch all journal entries with pagination
    journal_entries = fetch_all_paginated(
        access_token,
        realm_id,
        f"SELECT * FROM JournalEntry WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'",
        "JournalEntry"
    )

    return {
        "purchases": {"QueryResponse": {"Purchase": purchases}},
        "bills": {"QueryResponse": {"Bill": bills}},
        "journal_entries": {"QueryResponse": {"JournalEntry": journal_entries}}
    }


def fetch_accounts(access_token: str, realm_id: str) -> dict:
    """
    Fetch Chart of Accounts from QuickBooks to get account hierarchy.

    Args:
        access_token: QuickBooks OAuth access token
        realm_id: QuickBooks company/realm ID

    Returns:
        Account query response as dict
    """
    all_accounts = []
    start_position = 1
    max_results = 1000

    while True:
        result = qb_api_request(
            access_token,
            realm_id,
            "query",
            params={"query": f"SELECT * FROM Account STARTPOSITION {start_position} MAXRESULTS {max_results}"}
        )

        accounts = result.get("QueryResponse", {}).get("Account", [])
        if not accounts:
            break

        all_accounts.extend(accounts)

        if len(accounts) < max_results:
            break

        start_position += len(accounts)

    return {"QueryResponse": {"Account": all_accounts}}


# ============================================================================
# Account Mapping
# ============================================================================

def build_account_mapping(accounts_data: dict) -> dict:
    """
    Build a mapping from account ID and name to full hierarchical path.

    Args:
        accounts_data: Account query response from fetch_accounts()

    Returns:
        Dict with two sub-dicts:
        - by_id: {account_id: full_path}
        - by_name: {leaf_name: full_path} (for accounts without ID in transactions)
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
# Budget Parsing
# ============================================================================

def parse_budgets(budget_response: dict, account_mapping: dict = None) -> dict:
    """
    Parse QuickBooks Budget entity response into a lookup by full account path.

    Args:
        budget_response: Budget query response from fetch_budgets()
        account_mapping: Optional dict with 'by_id' mapping account IDs to full paths

    Returns:
        Dict like: {"Expenses:Board:Tech Team:Internet access": 3230, ...}
    """
    budgets_by_account = {}
    by_id = account_mapping.get("by_id", {}) if account_mapping else {}

    # Get budgets from QueryResponse
    budgets = budget_response.get("QueryResponse", {}).get("Budget", [])

    if not budgets:
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
            break

    if not target_budget:
        # Try any P&L budget
        for budget in budgets:
            if budget.get("BudgetType") == "ProfitAndLoss":
                target_budget = budget
                break

    if not target_budget:
        return budgets_by_account

    # Extract budget details by account
    for detail in target_budget.get("BudgetDetail", []):
        account_ref = detail.get("AccountRef", {})
        account_id = account_ref.get("value", "")
        account_name = account_ref.get("name", "")
        amount = detail.get("Amount", 0)

        if not amount:
            continue

        # Try to resolve account ID to full path, fall back to name
        if account_id and account_id in by_id:
            full_path = by_id[account_id]
        else:
            # Fall back to name (may be short or full depending on QB response)
            full_path = account_name

        if full_path:
            # Accumulate amounts for the same account (monthly entries sum to annual)
            budgets_by_account[full_path] = budgets_by_account.get(full_path, 0) + float(amount)

    return budgets_by_account


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
                    accounts[name] = balance
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

    Args:
        qb_data: Current period balance sheet from QB API
        prior_data: Optional prior period balance sheet (e.g., start of year)

    Returns:
        Dashboard format dict with bank, investments, total, and metadata
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
    if parent_path == header:
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


def match_budget_to_committee(committee_name: str, budgets: dict) -> float:
    """
    Match a committee name to budget amounts.

    Args:
        committee_name: Committee name like "Board", "Common House"
        budgets: Dict of {full_account_path: amount}

    Returns:
        Total budget for this committee
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
        "utilities": ["Utilities:"],
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

    Args:
        qb_data: P&L report from QuickBooks
        budgets: Optional dict of budget amounts by account name

    Returns:
        Dashboard format dict with committees and metadata
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

    Returns:
        Dict with 'transactions' list and 'metadata'
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

        # Last resort: return the name as-is
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

            # Only include debit entries to expense accounts
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
    """
    Create summary.json combining cash and budget data.

    Args:
        cash_data: Transformed cash/investments data from transform_balance_sheet()
        budget_data: Transformed budget data from transform_profit_and_loss()

    Returns:
        Summary dict with high-level financial metrics
    """
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
