import os
import json
import io
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from stravalib.client import Client
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import pandas as pd
import logging
from typing import List, Optional, Dict
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('strava_exporter')

# Define the project's base directory
BASE_DIR = Path(__file__).resolve().parent.parent

class StravaExporter:
    def __init__(self, config_path: str = None):
        """
        Initialize the Strava exporter with configuration options.

        Args:
            config_path: Path to configuration file
        """
        if config_path is None:
            config_path = BASE_DIR / 'config' / 'config.json'

        self.config = self._load_config(config_path)
        load_dotenv(dotenv_path=BASE_DIR / '.env')
        self.strava_client = Client()
        self.google_drive_service = None
        self.strava_token_file = BASE_DIR / 'config' / 'strava_token.json'
        self.google_token_file = BASE_DIR / 'config' / 'token.json'
        self.google_creds_file = BASE_DIR / 'config' / 'credentials.json'
        self.json_export_file = BASE_DIR / 'data' / 'strava_export.json'

        # Ensure the data directory exists
        self.json_export_file.parent.mkdir(parents=True, exist_ok=True)

        self.setup_credentials()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}. Using default settings.")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            raise

    def setup_credentials(self):
        """Set up credentials for Strava and Google Drive."""
        # Strava credentials
        self._load_and_refresh_strava_token()

        # Google credentials
        SCOPES = ['https://www.googleapis.com/auth/drive.file']  # Only Drive scope is needed
        creds = None

        if os.path.exists(self.google_token_file):
            creds = Credentials.from_authorized_user_file(self.google_token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.google_creds_file, SCOPES)
                creds = flow.run_console()

            with open(self.google_token_file, 'w') as token:
                creds_data = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }
                token.write(json.dumps(creds_data, indent=4))

        self.google_drive_service = build('drive', 'v3', credentials=creds)

    def _load_and_refresh_strava_token(self):
        """Loads Strava token from file and refreshes if expired."""
        try:
            # Check if the file is empty to avoid JSONDecodeError
            if os.path.getsize(self.strava_token_file) == 0:
                logger.error(f"Token file {self.strava_token_file} is empty. Please ensure the STRAVA_TOKEN_JSON secret is set correctly in your repository.")
                raise FileNotFoundError

            with open(self.strava_token_file, 'r') as f:
                token_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Token file {self.strava_token_file} not found. Please run strava_auth.py first.")
            raise

        if datetime.now().timestamp() > token_data['expires_at']:
            logger.info("Strava token expired, refreshing...")
            client = Client()
            new_token = client.refresh_access_token(
                client_id=os.getenv('STRAVA_CLIENT_ID'),
                client_secret=os.getenv('STRAVA_CLIENT_SECRET'),
                refresh_token=token_data['refresh_token']
            )
            with open(self.strava_token_file, 'w') as f:
                json.dump(new_token, f, indent=2)
            token_data = new_token
            logger.info("Strava token refreshed and saved.")

        self.strava_client.access_token = token_data['access_token']

    def get_strava_activities_since(self, since_date: datetime) -> List[Dict]:
        """Fetch activities from Strava since a given date in weekly batches."""
        all_activities = []
        start_date = since_date
        end_date = datetime.now(timezone.utc)

        current_start = start_date
        while current_start < end_date:
            current_end = min(current_start + timedelta(days=7), end_date)
            logger.info(f"Fetching activities from {current_start.date()} to {current_end.date()}")
            
            try:
                activities_iterator = self.strava_client.get_activities(
                    after=current_start,
                    before=current_end
                )
                activities_in_batch = list(activities_iterator)
                if activities_in_batch:
                    all_activities.extend(activities_in_batch)
                logger.info(f"Found {len(activities_in_batch)} activities in this batch.")

            except Exception as e:
                logger.error(f"Error fetching batch from {current_start.date()} to {current_end.date()}: {e}")
            
            current_start += timedelta(days=7)

        return all_activities

    def format_data_for_json(self, activities):
        """Formats activity and split data into the V2 nested JSON structure."""
        workouts_list = []
        for summary_activity in activities:
            activity = self.strava_client.get_activity(summary_activity.id)

            # Add detailed data if available
            splits_data = []
            if activity.laps:
                for lap in activity.laps:
                    split_info = {
                        'split_number': lap.split,
                        'distance_meters': float(lap.distance) if lap.distance else 0,
                        'elapsed_time_seconds': lap.elapsed_time.total_seconds(),
                        'moving_time_seconds': lap.moving_time.total_seconds(),
                        'average_speed_mps': float(lap.average_speed) if lap.average_speed else 0,
                        'average_heartrate': lap.average_heartrate,
                        'max_heartrate': lap.max_heartrate,
                        'average_watts': lap.average_watts
                    }
                    splits_data.append(split_info)

            # Basic activity data
            workout_data = {
                'id': str(activity.id),
                'name': activity.name,
                'type': activity.type,
                'start_date': activity.start_date.isoformat(),
                'distance_meters': float(activity.distance) if activity.distance else 0,
                'elapsed_time_seconds': activity.elapsed_time.total_seconds(),
                'moving_time_seconds': activity.moving_time.total_seconds(),
                'total_elevation_gain_meters': float(activity.total_elevation_gain) if activity.total_elevation_gain else 0,
                'average_speed_mps': float(activity.average_speed) if activity.average_speed else 0,
                'max_speed_mps': float(activity.max_speed) if activity.max_speed else 0,
                'description': activity.description,
                'device_name': activity.device_name,
                'gear_id': activity.gear_id,
                'heartrate': {
                    'average': activity.average_heartrate,
                    'max': activity.max_heartrate
                },
                'power': {
                    'average_watts': activity.average_watts
                },
                'relative_effort': activity.suffer_score,
                'splits': splits_data
            }
            workouts_list.append(workout_data)

        return {
            'metadata': {
                'schema_version': '2.0',
                'exported_at': datetime.now().isoformat()
            },
            'workouts': workouts_list
        }

    def download_from_google_drive(self, remote_filename, local_filepath):
        """Downloads a file from Google Drive if it exists."""
        try:
            query = f"name='{remote_filename}' and trashed=false"
            response = self.google_drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = response.get('files', [])

            if files:
                file_id = files[0].get('id')
                request = self.google_drive_service.files().get_media(fileId=file_id)
                fh = io.FileIO(local_filepath, 'wb')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    logger.info(f"Download {int(status.progress() * 100)}%.")
                logger.info(f"Successfully downloaded '{remote_filename}' from Google Drive.")
                return True
            else:
                logger.info(f"'{remote_filename}' not found in Google Drive. A new file will be created.")
                return False
        except HttpError as e:
            logger.error(f"An error occurred while downloading from Google Drive: {e}")
            return False

    def upload_to_google_drive(self, local_filepath, remote_filename):
        """Uploads a file to Google Drive, updating it if it exists."""
        try:
            # Check if the file already exists
            query = f"name='{remote_filename}' and trashed=false"
            response = self.google_drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = response.get('files', [])

            media = MediaFileUpload(local_filepath, mimetype='application/json', resumable=True)

            if files:
                # File exists, update it
                file_id = files[0].get('id')
                self.google_drive_service.files().update(fileId=file_id, media_body=media).execute()
                logger.info(f"Successfully updated '{remote_filename}' in Google Drive.")
            else:
                # File does not exist, create it
                file_metadata = {'name': remote_filename}
                self.google_drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                logger.info(f"Successfully uploaded '{remote_filename}' to Google Drive.")
            return True
        except HttpError as e:
            logger.error(f"An error occurred while uploading to Google Drive: {e}")
            return False

    def write_to_json(self, data, filename=None):
        """Write data to a JSON file."""
        if filename is None:
            filename = self.json_export_file
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully wrote data to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to write to {filename}: {e}")
            return False

    def run_export(self, days_back: Optional[int] = 90):
        """Main function to run the export process with incremental updates."""
        try:
            if days_back is None:
                days_back = self.config.get('days_back', 90)

            # Download existing data from Google Drive
            existing_data = None
            if self.download_from_google_drive('strava_export.json', self.json_export_file):
                with open(self.json_export_file, 'r') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning("Could not decode existing JSON file. Starting fresh.")
                        existing_data = None

            # Determine the last fetch date
            last_fetch_date = None
            if existing_data and 'workouts' in existing_data and existing_data['workouts']:
                valid_dates = []
                for w in existing_data['workouts']:
                    date_str = w.get('start_date_local') or w.get('start_date')
                    if date_str:
                        valid_dates.append(datetime.fromisoformat(date_str))
                
                if valid_dates:
                    last_fetch_date = max(valid_dates)
                    logger.info(f"Last fetched activity date: {last_fetch_date}")
                else:
                    last_fetch_date = None
            else:
                # If no existing data, fetch all activities for the specified period
                last_fetch_date = datetime.now(timezone.utc) - timedelta(days=days_back)
                logger.info(f"No existing data found. Fetching activities since {last_fetch_date.date()}")

            # Fetch new activities since the last fetch date
            logger.info(f"Fetching new activities since {last_fetch_date.date()}...")
            new_activities = self.get_strava_activities_since(last_fetch_date)

            if not new_activities:
                logger.info("No new activities found.")
            else:
                logger.info(f"Found {len(new_activities)} new activities.")

            # Merge new activities with existing data
            if existing_data and 'workouts' in existing_data:
                # Create a set of existing IDs for quick lookup
                existing_ids = {w['id'] for w in existing_data['workouts']}
                # Format and add only new activities
                formatted_new = self.format_data_for_json(new_activities)['workouts']
                for workout in formatted_new:
                    if workout['id'] not in existing_ids:
                        existing_data['workouts'].append(workout)
                # Sort workouts by date
                existing_data['workouts'].sort(key=lambda w: (w.get('start_date_local') or w.get('start_date')), reverse=True)
                final_data = existing_data
            else:
                final_data = self.format_data_for_json(new_activities)

            # Prune workouts older than the threshold
            cutoff_date = datetime.now() - timedelta(days=days_back)
            if 'workouts' in final_data:
                original_count = len(final_data['workouts'])
                final_data['workouts'] = [
                    w for w in final_data['workouts'] 
                    if datetime.fromisoformat(w.get('start_date_local') or w.get('start_date')) >= cutoff_date
                ]
                pruned_count = original_count - len(final_data['workouts'])
                if pruned_count > 0:
                    logger.info(f"Pruned {pruned_count} workouts older than {days_back} days.")

            # Update metadata and write to file
            final_data['metadata'] = {
                'schema_version': '2.0',
                'exported_at': datetime.now().isoformat()
            }

            if self.write_to_json(final_data, self.json_export_file):
                logger.info("Uploading updated JSON export to Google Drive...")
                if self.upload_to_google_drive(self.json_export_file, 'strava_export.json'):
                    logger.info("JSON export uploaded successfully.")
                else:
                    logger.error("Failed to upload JSON export.")

        except Exception as e:
            logger.error(f"Error during export: {str(e)}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export Strava activities to a JSON file and upload to Google Drive.')
    parser.add_argument('--days-back', type=int, default=None,
                       help='Number of days to look back for activities')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    exporter = StravaExporter(config_path=args.config)
    exporter.run_export(days_back=args.days_back)
