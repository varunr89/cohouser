import azure.functions as func
import logging
import os
import json
import requests
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient

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
