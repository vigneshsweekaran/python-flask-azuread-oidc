import os
import msal
from flask import Flask, request, session, redirect, url_for, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Azure AD OIDC Configuration
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
SCOPE = ["email"]  # openid and profile are added automatically by MSAL
REDIRECT_PATH = "/get-token"

# This creates a Confidential Client Application instance
client = msal.ConfidentialClientApplication(
    client_id=AZURE_CLIENT_ID,
    client_credential=AZURE_CLIENT_SECRET,
    authority=AUTHORITY
)

@app.route("/")
def index():
    if not session.get("user"):
        return render_template("login.html")
    return render_template("index.html")

@app.route("/login")
def login():
    # MSAL will store the auth flow state in the session
    session["flow"] = client.initiate_auth_code_flow(
        scopes=SCOPE,
        redirect_uri=url_for("get_token", _external=True)
    )
    return redirect(session["flow"]["auth_uri"])

@app.route(REDIRECT_PATH)
def get_token():
    try:
        # Use the state stored in the session to complete the auth flow
        result = client.acquire_token_by_auth_code_flow(
            session.get("flow", {}),
            request.args
        )

        if "error" in result:
            return f"Login Error: {result.get('error')}: {result.get('error_description')}", 500

        # The user's claims are in the 'id_token_claims' dictionary
        session["user"] = result.get("id_token_claims")

    except ValueError as e:
        return f"Error: {e}"

    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()  # Clear the local session
    # Redirect user to Azure AD logout endpoint
    logout_url = (
        f"{AUTHORITY}/oauth2/v2.0/logout?"
        f"post_logout_redirect_uri={url_for('index', _external=True)}"
    )
    return redirect(logout_url)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)