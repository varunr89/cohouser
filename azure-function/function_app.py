import azure.functions as func
import logging
import os
import json
import requests
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient, ContentSettings
import qb_core

app = func.FunctionApp()

@app.route(route="callback", auth_level=func.AuthLevel.ANONYMOUS)
def oauth_callback(req: func.HttpRequest) -> func.HttpResponse:
    """Handle OAuth callback from QuickBooks."""
    logging.info("OAuth callback received")

    # Extract authorization code and realm ID from query params
    code = req.params.get("code")
    realm_id = req.params.get("realmId")
    error = req.params.get("error")

    if error:
        logging.error(f"OAuth error: {error}")
        return func.HttpResponse(
            body=create_error_html(error),
            mimetype="text/html",
            status_code=400
        )

    if not code or not realm_id:
        logging.error("Missing code or realmId")
        return func.HttpResponse(
            body=create_error_html("Missing authorization code or realm ID"),
            mimetype="text/html",
            status_code=400
        )

    # Exchange code for tokens
    try:
        tokens = exchange_code_for_tokens(code, realm_id)
    except Exception as e:
        logging.error(f"Token exchange failed: {e}")
        return func.HttpResponse(
            body=create_error_html(f"Token exchange failed: {e}"),
            mimetype="text/html",
            status_code=500
        )

    # Store tokens in Azure Blob Storage
    try:
        store_tokens(realm_id, tokens)
    except Exception as e:
        logging.error(f"Token storage failed: {e}")
        return func.HttpResponse(
            body=create_error_html(f"Token storage failed: {e}"),
            mimetype="text/html",
            status_code=500
        )

    logging.info(f"OAuth successful for realm {realm_id}")
    return func.HttpResponse(
        body=create_success_html(),
        mimetype="text/html",
        status_code=200
    )


def exchange_code_for_tokens(code: str, realm_id: str) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    client_id = os.environ["QB_CLIENT_ID"]
    client_secret = os.environ["QB_CLIENT_SECRET"]
    redirect_uri = os.environ.get("QB_REDIRECT_URI", "")

    token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

    response = requests.post(
        token_endpoint,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        auth=(client_id, client_secret),
        headers={"Accept": "application/json"},
    )

    if response.status_code != 200:
        raise Exception(f"Token endpoint returned {response.status_code}: {response.text}")

    token_data = response.json()

    return {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "expires_in": token_data["expires_in"],
        "x_refresh_token_expires_in": token_data["x_refresh_token_expires_in"],
        "realm_id": realm_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def store_tokens(realm_id: str, tokens: dict) -> None:
    """Store tokens in Azure Blob Storage."""
    connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    blob_service = BlobServiceClient.from_connection_string(connection_string)

    container_name = "qb-tokens"
    container_client = blob_service.get_container_client(container_name)

    # Create container if it doesn't exist
    try:
        container_client.create_container()
    except Exception:
        pass  # Container already exists

    blob_client = container_client.get_blob_client(f"{realm_id}/tokens.json")
    blob_client.upload_blob(json.dumps(tokens, indent=2), overwrite=True)


def create_success_html() -> str:
    """Generate success page HTML."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authorization Successful</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                   display: flex; justify-content: center; align-items: center;
                   min-height: 100vh; margin: 0; background: #f5f5f5; }
            .card { background: white; padding: 40px; border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
            .check { font-size: 48px; color: #4CAF50; }
            h1 { color: #333; margin: 20px 0 10px; }
            p { color: #666; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="check">&#10004;</div>
            <h1>Success!</h1>
            <p>QuickBooks has been connected successfully.</p>
            <p>You can close this window.</p>
        </div>
    </body>
    </html>
    """


def create_error_html(error: str) -> str:
    """Generate error page HTML."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authorization Failed</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                   display: flex; justify-content: center; align-items: center;
                   min-height: 100vh; margin: 0; background: #f5f5f5; }}
            .card {{ background: white; padding: 40px; border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
            .x {{ font-size: 48px; color: #f44336; }}
            h1 {{ color: #333; margin: 20px 0 10px; }}
            p {{ color: #666; }}
            .error {{ color: #f44336; font-family: monospace; margin-top: 20px;
                     padding: 10px; background: #fff5f5; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="x">&#10008;</div>
            <h1>Authorization Failed</h1>
            <p>Something went wrong connecting to QuickBooks.</p>
            <div class="error">{error}</div>
            <p>Please contact the dashboard administrator.</p>
        </div>
    </body>
    </html>
    """


@app.timer_trigger(schedule="0 0 14 * * *", arg_name="timer", run_on_startup=False)
def refresh_data(timer: func.TimerRequest) -> None:
    """Refresh QuickBooks data daily at 6 AM Pacific (14:00 UTC)."""
    logging.info("Starting scheduled data refresh")

    status = {
        "last_attempt": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "error": None
    }

    try:
        # Load configuration
        client_id = os.environ["QB_CLIENT_ID"]
        client_secret = os.environ["QB_CLIENT_SECRET"]
        realm_id = os.environ["QB_REALM_ID"]
        connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

        # Get tokens from blob storage
        tokens = load_tokens(connection_string, realm_id)

        # Refresh access token
        new_tokens = qb_core.refresh_access_token(
            client_id, client_secret, tokens["refresh_token"]
        )

        # Save updated tokens back to blob
        save_tokens(connection_string, realm_id, {
            **tokens,
            "access_token": new_tokens["access_token"],
            "refresh_token": new_tokens["refresh_token"],
            "token_refreshed_at": datetime.now(timezone.utc).isoformat()
        })

        access_token = new_tokens["access_token"]

        # Fetch data from QuickBooks
        year = datetime.now().year
        start_of_year = f"{year}-01-01"
        end_date = datetime.now().strftime("%Y-%m-%d")

        balance_sheet = qb_core.fetch_balance_sheet(access_token, realm_id)
        balance_sheet_prior = qb_core.fetch_balance_sheet_prior(access_token, realm_id, start_of_year)
        profit_loss = qb_core.fetch_profit_and_loss(access_token, realm_id)
        budgets_raw = qb_core.fetch_budgets(access_token, realm_id)
        transactions_raw = qb_core.fetch_transactions(access_token, realm_id, start_of_year, end_date)
        accounts_raw = qb_core.fetch_accounts(access_token, realm_id)

        # Transform data
        budgets = qb_core.parse_budgets(budgets_raw)
        account_mapping = qb_core.build_account_mapping(accounts_raw)

        cash_data = qb_core.transform_balance_sheet(balance_sheet, balance_sheet_prior)
        budget_data = qb_core.transform_profit_and_loss(profit_loss, budgets)
        transactions_data = qb_core.transform_transactions(transactions_raw, account_mapping)
        summary_data = qb_core.create_summary(cash_data, budget_data)

        # Write to blob storage
        today = datetime.now().strftime("%Y-%m-%d")
        write_data_to_blob(connection_string, cash_data, budget_data, transactions_data, summary_data, today)

        # Update status
        status["last_success"] = datetime.now(timezone.utc).isoformat()
        status["status"] = "success"
        status["data_date"] = today

        logging.info(f"Data refresh completed successfully for {today}")

    except Exception as e:
        logging.error(f"Data refresh failed: {e}")
        status["status"] = "failed"
        status["error"] = str(e)

    # Always write status (even on failure)
    try:
        write_status_to_blob(os.environ["AZURE_STORAGE_CONNECTION_STRING"], status)
    except Exception as e:
        logging.error(f"Failed to write status: {e}")


def load_tokens(connection_string: str, realm_id: str) -> dict:
    """Load tokens from blob storage."""
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client("qb-tokens")
    blob_client = container_client.get_blob_client(f"{realm_id}/tokens.json")
    blob_data = blob_client.download_blob().readall()
    return json.loads(blob_data)


def save_tokens(connection_string: str, realm_id: str, tokens: dict) -> None:
    """Save tokens to blob storage."""
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client("qb-tokens")
    blob_client = container_client.get_blob_client(f"{realm_id}/tokens.json")
    blob_client.upload_blob(json.dumps(tokens, indent=2), overwrite=True)


def write_data_to_blob(connection_string: str, cash_data: dict, budget_data: dict,
                       transactions_data: dict, summary_data: dict, date_str: str) -> None:
    """Write all data files to blob storage."""
    blob_service = BlobServiceClient.from_connection_string(connection_string)

    # Ensure container exists with public access
    container_client = blob_service.get_container_client("qb-data")
    try:
        container_client.create_container(public_access="blob")
    except Exception:
        pass  # Container exists

    files = {
        "cash-investments.json": cash_data,
        "budget-vs-actual.json": budget_data,
        "transactions.json": transactions_data,
        "summary.json": summary_data,
    }

    for filename, data in files.items():
        content = json.dumps(data, indent=2)

        # Write to latest/
        blob_client = container_client.get_blob_client(f"latest/{filename}")
        blob_client.upload_blob(content, overwrite=True, content_settings=ContentSettings(content_type="application/json"))

        # Write to history/{date}/
        blob_client = container_client.get_blob_client(f"history/{date_str}/{filename}")
        blob_client.upload_blob(content, overwrite=True, content_settings=ContentSettings(content_type="application/json"))


def write_status_to_blob(connection_string: str, status: dict) -> None:
    """Write status.json to blob storage."""
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client("qb-data")
    blob_client = container_client.get_blob_client("latest/status.json")
    blob_client.upload_blob(
        json.dumps(status, indent=2),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json")
    )
