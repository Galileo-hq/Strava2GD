import os
import json
from dotenv import load_dotenv
from stravalib.client import Client
from pathlib import Path

# Define the project's base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file in the project root
load_dotenv(dotenv_path=BASE_DIR / '.env')

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
TOKEN_FILE = BASE_DIR / 'config' / 'strava_token.json'

def main():
    """
    Performs the one-time Strava OAuth2 flow to get a refresh token.
    """
    if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET:
        print("Error: STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be set in your .env file.")
        return

    client = Client()
    
    # The redirect_uri must match what you've set in your Strava API settings.
    # For a local script, 'http://localhost' or 'http://localhost:8000' is common.
    redirect_uri = 'http://localhost'
    
    # Request all necessary scopes, especially activity:read_all
    scopes = ['read', 'activity:read_all']
    
    authorize_url = client.authorization_url(
        client_id=STRAVA_CLIENT_ID,
        redirect_uri=redirect_uri,
        scope=scopes
    )

    print("\n--- Strava Authentication ---")
    print("1. Go to this URL in your browser:")
    print(f"\n   {authorize_url}\n")
    print(f"2. Authorize the application, and you will be redirected to a URL like:")
    print(f"   '{redirect_uri}/?state=&code=YOUR_CODE&scope=read,activity:read_all'\n")
    print("3. Copy the value of the 'code' parameter from that URL and paste it below.")

    auth_code = input("\nEnter the authorization code: ").strip()

    try:
        token_response = client.exchange_code_for_token(
            client_id=STRAVA_CLIENT_ID,
            client_secret=STRAVA_CLIENT_SECRET,
            code=auth_code
        )

        # Save the token data to a file
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_response, f, indent=2)
        
        print(f"\nSuccess! Token data saved to {TOKEN_FILE}")
        print("You can now run the main strava_exporter.py script.")

    except Exception as e:
        print(f"\nError exchanging code for token: {e}")

if __name__ == "__main__":
    main()
