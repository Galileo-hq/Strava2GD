import os
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Define the project's base directory
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / 'config'
GOOGLE_CREDS_FILE = CONFIG_DIR / 'credentials.json'
GOOGLE_TOKEN_FILE = CONFIG_DIR / 'token.json'

# The SCOPES must match the scopes used in your original script
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate():
    """Runs the Google authentication flow and saves the token."""
    creds = None

    # The file token.json stores the user's access and refresh tokens.
    # It's created automatically when the authorization flow completes for the first time.
    if os.path.exists(GOOGLE_TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Error loading token file: {e}. A new token will be generated.")
            creds = None

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token has expired, attempting to refresh...")
            try:
                creds.refresh(Request())
                print("Token refreshed successfully.")
            except Exception as e:
                print(f"Could not refresh token: {e}")
                print("Proceeding to re-authenticate to get a new refresh token.")
                creds = None  # Force re-authentication
        
        if not creds:
            print("A new authentication is required.")
            if not os.path.exists(GOOGLE_CREDS_FILE):
                print(f"Error: Google credentials file not found at {GOOGLE_CREDS_FILE}")
                print("Please make sure you have your 'credentials.json' from the Google Cloud Console in the 'config' directory.")
                return

            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(GOOGLE_TOKEN_FILE, 'w') as token_file:
            creds_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
            token_file.write(json.dumps(creds_data, indent=4))
        
        print(f"\nAuthentication successful. Token saved to {GOOGLE_TOKEN_FILE}")
        print("\n--- ACTION REQUIRED ---")
        print("Copy the entire content of the file 'config/token.json' and paste it into your GitHub repository's `GOOGLE_TOKEN_JSON` secret.")
        print("This is a critical step for the GitHub Actions workflow to succeed.")
    else:
        print("Google token is still valid. No action needed.")

if __name__ == '__main__':
    # Ensure the config directory exists
    CONFIG_DIR.mkdir(exist_ok=True)
    authenticate()
