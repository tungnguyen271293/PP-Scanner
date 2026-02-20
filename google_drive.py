import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Set up Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """Authenticates and returns the Google Drive service object."""
    # Look for the credentials in an environment variable FIRST
    # (This is how Streamlit Cloud Secrets will inject it)
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES
            )
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Error loading credentials from environment: {e}")
            
    # Fallback to local file if not in environment
    if os.path.exists("service_account.json"):
        creds = service_account.Credentials.from_service_account_file(
            "service_account.json", scopes=SCOPES
        )
        return build('drive', 'v3', credentials=creds)
    
    raise Exception("Google Credentials not found. Please configure the GOOGLE_CREDENTIALS environment variable or provide a service_account.json file.")

def upload_screenshot_to_drive(file_path, folder_id=None):
    """
    Uploads a file to Google Drive and makes it accessible via a link.
    If folder_id is provided, the file is uploaded to that specific folder.
    """
    try:
        service = get_drive_service()
        file_name = os.path.basename(file_path)

        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, mimetype='image/png')
        
        # Upload the file
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # Wait a moment for propagation
        import time
        time.sleep(1)

        return file_id

    except Exception as e:
        print(f"An error occurred during Google Drive upload: {e}")
        return None
