#!/usr/bin/env python3
"""
Wild Whatcom Financial Data Processing Script
Reads CSV files and generates static JSON files for the dashboard
"""

import pandas as pd
import json
import os
from pathlib import Path
import numpy as np

# Paths
DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'wild_whatcom_finance'
OUTPUT_DIR = Path(__file__).parent.parent / 'public' / 'data'

def clean_currency(value):
    """Convert currency strings to float"""
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Handle Excel errors
        if value.startswith('#') or value == '':
            return 0
        cleaned = value.replace('$', '').replace(',', '').strip()
        return float(cleaned) if cleaned else 0
    return 0

def safe_float(value):
    """Safely convert to float, handling errors"""
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.startswith('#'):
        return 0
    try:
        return float(value)
    except:
        return 0

def safe_divide(numerator, denominator):
    """Safely divide, returning 0 if denominator is 0"""
    if denominator == 0:
        return 0
    return numerator / denominator

def load_summary_data():
    """Load and process the summary financial data"""
    file_path = DATA_DIR / 'Updated WW Long term financial planning FY19-FY25 - Summary.csv'
    df = pd.read_csv(file_path)

    # Extract key metrics from the summary
    summary = {
        'fy26_projected_income': clean_currency(df.iloc[2, 3]),
        'fy26_projected_expenses': clean_currency(df.iloc[3, 3]),
        'fy26_projected_equity': clean_currency(df.iloc[4, 3]),
        'fy26_projected_assets': clean_currency(df.iloc[5, 3]),
    }

    # Extract historical trends (FY19-FY29)
    years = ['FY19', 'FY20', 'FY21', 'FY22', 'FY23', 'FY24', 'FY25', 'FY26', 'FY27', 'FY28', 'FY29']

    # Income trends (row 18 onwards)
    income_trends = {
        'years': years,
        'program_revenue': [],
        'individual_donors': [],
        'grants': [],
        'business_sponsors': [],
        'events': [],
        'other': [],
        'total': []
    }

    # Get data from rows (FY19 is col 2, FY29 is col 12)
    for col_idx in range(2, 13):
        income_trends['program_revenue'].append(clean_currency(df.iloc[17, col_idx]))
        income_trends['individual_donors'].append(clean_currency(df.iloc[18, col_idx]))
        income_trends['grants'].append(clean_currency(df.iloc[19, col_idx]))
        income_trends['business_sponsors'].append(clean_currency(df.iloc[20, col_idx]))
        income_trends['events'].append(clean_currency(df.iloc[21, col_idx]))
        income_trends['other'].append(clean_currency(df.iloc[22, col_idx]))
        income_trends['total'].append(clean_currency(df.iloc[24, col_idx]))

    # Expense trends (payroll + operating)
    expense_trends = {
        'years': years,
        'salaries_wages_benefits': [],
        'operating_expenses': [],
        'total': []
    }

    for col_idx in range(2, 13):
        expense_trends['salaries_wages_benefits'].append(clean_currency(df.iloc[10, col_idx]))
        expense_trends['operating_expenses'].append(clean_currency(df.iloc[11, col_idx]))
        expense_trends['total'].append(clean_currency(df.iloc[13, col_idx]))

    # Net income and reserves
    financial_health = {
        'years': years,
        'net_income': [],
        'retained_earnings': [],
        'months_in_reserve': []
    }

    for col_idx in range(2, 13):
        financial_health['net_income'].append(clean_currency(df.iloc[28, col_idx]))
        financial_health['retained_earnings'].append(clean_currency(df.iloc[26, col_idx]))
        months = df.iloc[32, col_idx]
        financial_health['months_in_reserve'].append(float(months) if pd.notna(months) and months != '' else 0)

    return {
        'summary': summary,
        'income_trends': income_trends,
        'expense_trends': expense_trends,
        'financial_health': financial_health
    }

def load_fy26_annual_data():
    """Load FY26 budget vs actuals"""
    file_path = DATA_DIR / 'FY 26 Cash Flow Projections (budget+actuals)  - Annual.csv'
    df = pd.read_csv(file_path)

    # Extract revenue data (rows 6-13)
    revenue = {
        'contributions': {
            'budgeted': clean_currency(df.iloc[6, 1]),
            'actual': clean_currency(df.iloc[6, 2]),
            'fy25_actual': clean_currency(df.iloc[6, 4]),
            'fy24_actual': clean_currency(df.iloc[6, 5])
        },
        'grants': {
            'budgeted': clean_currency(df.iloc[7, 1]),
            'actual': clean_currency(df.iloc[7, 2]),
            'fy25_actual': clean_currency(df.iloc[7, 4]),
            'fy24_actual': clean_currency(df.iloc[7, 5])
        },
        'earned_revenue': {
            'budgeted': clean_currency(df.iloc[8, 1]),
            'actual': clean_currency(df.iloc[8, 2]),
            'fy25_actual': clean_currency(df.iloc[8, 4]),
            'fy24_actual': clean_currency(df.iloc[8, 5])
        },
        'fundraising_events': {
            'budgeted': clean_currency(df.iloc[10, 1]),
            'actual': clean_currency(df.iloc[10, 2]),
            'fy25_actual': clean_currency(df.iloc[10, 4]),
            'fy24_actual': clean_currency(df.iloc[10, 5])
        },
        'sponsorships': {
            'budgeted': clean_currency(df.iloc[11, 1]),
            'actual': clean_currency(df.iloc[11, 2]),
            'fy25_actual': clean_currency(df.iloc[11, 4]),
            'fy24_actual': clean_currency(df.iloc[11, 5])
        },
        'other': {
            'budgeted': clean_currency(df.iloc[12, 1]),
            'actual': clean_currency(df.iloc[12, 2]),
            'fy25_actual': clean_currency(df.iloc[12, 4]),
            'fy24_actual': clean_currency(df.iloc[12, 5])
        },
        'total': {
            'budgeted': clean_currency(df.iloc[13, 1]),
            'actual': clean_currency(df.iloc[13, 2]),
            'fy25_actual': clean_currency(df.iloc[13, 4]),
            'fy24_actual': clean_currency(df.iloc[13, 5])
        }
    }

    # Extract major expense categories (simplified)
    expenses = {
        'salaries_wages': {
            'budgeted': clean_currency(df.iloc[16, 1]),
            'actual': clean_currency(df.iloc[16, 2]),
            'fy25_actual': clean_currency(df.iloc[16, 4]),
            'fy24_actual': clean_currency(df.iloc[16, 5])
        },
        'payroll_taxes': {
            'budgeted': clean_currency(df.iloc[17, 1]),
            'actual': clean_currency(df.iloc[17, 2]),
            'fy25_actual': clean_currency(df.iloc[17, 4]),
            'fy24_actual': clean_currency(df.iloc[17, 5])
        },
        'benefits': {
            'budgeted': clean_currency(df.iloc[19, 1]),
            'actual': clean_currency(df.iloc[19, 2]),
            'fy25_actual': clean_currency(df.iloc[19, 4]),
            'fy24_actual': clean_currency(df.iloc[19, 5])
        },
        'total': {
            'budgeted': clean_currency(df.iloc[57, 1]),
            'actual': clean_currency(df.iloc[57, 2]),
            'fy25_actual': clean_currency(df.iloc[57, 4]),
            'fy24_actual': clean_currency(df.iloc[57, 5])
        }
    }

    # Current reserves
    reserves = {
        'current_reserves': clean_currency(df.iloc[65, 1]),
        'months_reserve': float(df.iloc[66, 1]) if pd.notna(df.iloc[66, 1]) else 0,
        'one_month_expenses': clean_currency(df.iloc[63, 1]),
        'three_months_expenses': clean_currency(df.iloc[62, 1]),
        'six_months_expenses': clean_currency(df.iloc[61, 1])
    }

    return {
        'revenue': revenue,
        'expenses': expenses,
        'reserves': reserves
    }

def load_program_data():
    """Load program-level performance data"""
    file_path = DATA_DIR / 'FY 26 Cash Flow Projections (budget+actuals)  - high level Income review.csv'
    df = pd.read_csv(file_path)

    programs = {
        'explorers_club': {
            'budgeted': clean_currency(df.iloc[2, 1]),
            'actual': clean_currency(df.iloc[2, 2]),
            'percent_of_goal': safe_float(df.iloc[2, 3]),
            'scholarships': clean_currency(df.iloc[2, 6])
        },
        'community': {
            'budgeted': clean_currency(df.iloc[3, 1]),
            'actual': clean_currency(df.iloc[3, 2]),
            'percent_of_goal': safe_float(df.iloc[3, 3]),
            'scholarships': clean_currency(df.iloc[3, 6])
        },
        'school': {
            'budgeted': clean_currency(df.iloc[4, 1]),
            'actual': clean_currency(df.iloc[4, 2]),
            'percent_of_goal': safe_float(df.iloc[4, 3]),
            'scholarships': clean_currency(df.iloc[4, 6])
        },
        'nature_preschool': {
            'budgeted': clean_currency(df.iloc[5, 1]),
            'actual': clean_currency(df.iloc[5, 2]),
            'percent_of_goal': safe_float(df.iloc[5, 3]),
            'scholarships': clean_currency(df.iloc[5, 6])
        },
        'camps': {
            'budgeted': clean_currency(df.iloc[7, 1]),
            'actual': clean_currency(df.iloc[7, 2]),
            'scholarships': clean_currency(df.iloc[7, 6])
        }
    }

    return programs

def load_monthly_cashflow():
    """Load monthly cash flow projections"""
    file_path = DATA_DIR / 'FY 26 Cash Flow Projections (budget+actuals)  - R + E by monthyear.csv'
    df = pd.read_csv(file_path)

    months = ['Sept', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'Aug']

    # Revenue by month (row 6-13)
    revenue_by_month = {
        'months': months,
        'contributions': [],
        'grants': [],
        'earned_revenue': [],
        'events': [],
        'sponsorships': [],
        'other': [],
        'total': []
    }

    for col_idx in range(2, 14):  # Sept is col 2, Aug is col 13
        revenue_by_month['contributions'].append(clean_currency(df.iloc[6, col_idx]))
        revenue_by_month['grants'].append(clean_currency(df.iloc[7, col_idx]))
        revenue_by_month['earned_revenue'].append(clean_currency(df.iloc[8, col_idx]))
        revenue_by_month['events'].append(clean_currency(df.iloc[10, col_idx]))
        revenue_by_month['sponsorships'].append(clean_currency(df.iloc[11, col_idx]))
        revenue_by_month['other'].append(clean_currency(df.iloc[12, col_idx]))
        revenue_by_month['total'].append(clean_currency(df.iloc[13, col_idx]))

    # Expenses by month
    expense_by_month = {
        'months': months,
        'salaries_wages': [],
        'payroll_taxes': [],
        'benefits': [],
        'total': []
    }

    for col_idx in range(2, 14):
        expense_by_month['salaries_wages'].append(clean_currency(df.iloc[15, col_idx]))
        expense_by_month['payroll_taxes'].append(clean_currency(df.iloc[16, col_idx]))
        expense_by_month['benefits'].append(clean_currency(df.iloc[18, col_idx]))
        expense_by_month['total'].append(clean_currency(df.iloc[55, col_idx]))

    # Net income by month
    net_income_by_month = {
        'months': months,
        'net_income': [],
        'reserves': [],
        'months_in_reserve': []
    }

    for col_idx in range(2, 14):
        net_income_by_month['net_income'].append(clean_currency(df.iloc[57, col_idx]))
        net_income_by_month['reserves'].append(clean_currency(df.iloc[66, col_idx]))
        months_reserve = df.iloc[67, col_idx] if len(df) > 67 else 0
        net_income_by_month['months_in_reserve'].append(safe_float(months_reserve))

    return {
        'revenue_by_month': revenue_by_month,
        'expense_by_month': expense_by_month,
        'net_income_by_month': net_income_by_month
    }

def calculate_sankey_data(annual_data):
    """Calculate data for Sankey diagram"""
    revenue = annual_data['revenue']

    # Revenue sources
    sources = []
    targets = []
    values = []
    labels = [
        'Contributions',
        'Grants',
        'Earned Revenue',
        'Events',
        'Sponsorships',
        'Other',
        'Organization',
        'Payroll',
        'Operations'
    ]

    # Revenue flows to Organization
    sources.extend([0, 1, 2, 3, 4, 5])  # All revenue sources
    targets.extend([6, 6, 6, 6, 6, 6])  # All go to Organization
    values.extend([
        revenue['contributions']['actual'],
        revenue['grants']['actual'],
        revenue['earned_revenue']['actual'],
        revenue['fundraising_events']['actual'],
        revenue['sponsorships']['actual'],
        revenue['other']['actual']
    ])

    # Organization flows to expenses
    total_expenses = annual_data['expenses']['total']['actual']
    payroll_total = (annual_data['expenses']['salaries_wages']['actual'] +
                     annual_data['expenses']['payroll_taxes']['actual'] +
                     annual_data['expenses']['benefits']['actual'])
    operations_total = total_expenses - payroll_total

    sources.extend([6, 6])  # Organization
    targets.extend([7, 8])  # Payroll and Operations
    values.extend([payroll_total, operations_total])

    return {
        'labels': labels,
        'sources': sources,
        'targets': targets,
        'values': values
    }

def main():
    """Main processing function"""
    print("Starting data processing...")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load all data
    print("Loading summary data...")
    summary_data = load_summary_data()

    print("Loading FY26 annual data...")
    annual_data = load_fy26_annual_data()

    print("Loading program data...")
    program_data = load_program_data()

    print("Loading monthly cash flow...")
    cashflow_data = load_monthly_cashflow()

    print("Calculating Sankey diagram data...")
    sankey_data = calculate_sankey_data(annual_data)

    # Calculate executive summary metrics
    print("Calculating executive summary...")
    executive_summary = {
        'current_reserves': annual_data['reserves']['current_reserves'],
        'months_in_reserve': annual_data['reserves']['months_reserve'],
        'reserve_health': 'good' if annual_data['reserves']['months_reserve'] >= 3 else 'warning' if annual_data['reserves']['months_reserve'] >= 2 else 'critical',
        'ytd_revenue': annual_data['revenue']['total']['actual'],
        'ytd_revenue_budget': annual_data['revenue']['total']['budgeted'],
        'ytd_revenue_variance': safe_divide((annual_data['revenue']['total']['actual'] - annual_data['revenue']['total']['budgeted']), annual_data['revenue']['total']['budgeted']) * 100,
        'ytd_expenses': annual_data['expenses']['total']['actual'],
        'ytd_expenses_budget': annual_data['expenses']['total']['budgeted'],
        'ytd_expenses_variance': safe_divide((annual_data['expenses']['total']['actual'] - annual_data['expenses']['total']['budgeted']), annual_data['expenses']['total']['budgeted']) * 100,
        'net_income': annual_data['revenue']['total']['actual'] - annual_data['expenses']['total']['actual'],
        'reserve_targets': {
            'one_month': annual_data['reserves']['one_month_expenses'],
            'three_months': annual_data['reserves']['three_months_expenses'],
            'six_months': annual_data['reserves']['six_months_expenses']
        }
    }

    # Save all JSON files
    print("Saving JSON files...")

    with open(OUTPUT_DIR / 'executive_summary.json', 'w') as f:
        json.dump(executive_summary, f, indent=2)

    with open(OUTPUT_DIR / 'historical_trends.json', 'w') as f:
        json.dump(summary_data, f, indent=2)

    with open(OUTPUT_DIR / 'revenue_data.json', 'w') as f:
        json.dump(annual_data['revenue'], f, indent=2)

    with open(OUTPUT_DIR / 'expense_data.json', 'w') as f:
        json.dump(annual_data['expenses'], f, indent=2)

    with open(OUTPUT_DIR / 'program_data.json', 'w') as f:
        json.dump(program_data, f, indent=2)

    with open(OUTPUT_DIR / 'cashflow_data.json', 'w') as f:
        json.dump(cashflow_data, f, indent=2)

    with open(OUTPUT_DIR / 'sankey_data.json', 'w') as f:
        json.dump(sankey_data, f, indent=2)

    print(f"✅ Data processing complete! JSON files saved to {OUTPUT_DIR}")
    print(f"   - executive_summary.json")
    print(f"   - historical_trends.json")
    print(f"   - revenue_data.json")
    print(f"   - expense_data.json")
    print(f"   - program_data.json")
    print(f"   - cashflow_data.json")
    print(f"   - sankey_data.json")

if __name__ == '__main__':
    main()
