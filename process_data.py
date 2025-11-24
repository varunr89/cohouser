import pandas as pd
import json
import os

# Define file paths
data_dir = "data/wild_whatcom_finance"
annual_file = os.path.join(data_dir, "FY 26 Cash Flow Projections (budget+actuals)  - Annual.csv")

def process_annual_data(filepath):
    """
    Parses the Annual CSV to extract detailed Revenue and Expense data for multiple years.
    Returns a hierarchical structure: Year -> Type (Revenue/Expense) -> Category -> Value
    """
    # Read without header to handle complex structure manually
    df_raw = pd.read_csv(filepath, header=None)

    # Map columns based on analysis
    # 1: "FY26 Budget"
    # 4: "FY25 Actuals"
    # 5: "FY24 Actuals"
    # 7: "FY23 Actuals"
    # 9: "FY22 Actuals"
    # 11: "FY21 Actuals"
    # 13: "FY20 Actuals"
    # 15: "FY19 Actuals"

    col_map = {
        1: "FY26 Budget",
        4: "FY25 Actuals",
        5: "FY24 Actuals",
        7: "FY23 Actuals",
        9: "FY22 Actuals",
        11: "FY21 Actuals",
        13: "FY20 Actuals",
        15: "FY19 Actuals"
    }

    data_by_year = {year: {"Revenue": {}, "Expenses": {}} for year in col_map.values()}

    # Locate the row starting with "Revenue"
    try:
        revenue_row_idx = df_raw[df_raw[0] == "Revenue"].index[0]
    except IndexError:
        print("Could not find 'Revenue' section.")
        return {}

    current_section = "Revenue"

    # Iterate through rows starting after the header
    for idx in range(revenue_row_idx + 1, len(df_raw)):
        row = df_raw.iloc[idx]
        category = row[0]

        if pd.isna(category):
            continue

        category = str(category).strip()

        if category == "Expenses":
            current_section = "Expenses"
            continue

        if category in ["Total Revenue", "Total Expenses", "Net"]:
            continue

        # Stop if we hit bottom sections
        if "RESERVE FUNDING" in category:
            break

        # Extract values for each year
        for col_idx, year_label in col_map.items():
            val = row[col_idx]
            # Clean value (remove $, commas, handle parentheses)
            if pd.isna(val) or val == "-":
                val = 0
            else:
                try:
                    val = str(val).replace(",", "").replace("$", "").strip()
                    if "(" in val and ")" in val:
                         val = "-" + val.replace("(", "").replace(")", "")
                    val = float(val)
                except ValueError:
                    val = 0

            # Add to data structure if non-zero
            if val != 0:
                data_by_year[year_label][current_section][category] = val

    return data_by_year

def main():
    if not os.path.exists("src/data"):
        os.makedirs("src/data")

    annual_data = process_annual_data(annual_file)

    output = {
        "annual_data": annual_data,
        "meta": {
            "generated_at": pd.Timestamp.now().isoformat(),
            "source_files": [os.path.basename(annual_file)]
        }
    }

    # Save as JSON (standard)
    with open("src/data/financial_data.json", "w") as f:
        json.dump(output, f, indent=2)

    # Save as JS for static loading (window.FINANCIAL_DATA = ...)
    with open("src/data/financial_data.js", "w") as f:
        f.write("window.FINANCIAL_DATA = ")
        json.dump(output, f, indent=2)
        f.write(";")

    print("Data processing complete.")
    print(f"JSON saved to src/data/financial_data.json")
    print(f"JS saved to src/data/financial_data.js")

if __name__ == "__main__":
    main()
