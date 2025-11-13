#!/usr/bin/env python3
"""
Google Drive OAuth Setup Script

This script handles the initial OAuth 2.0 authentication flow for Google Drive API.
It will open a browser window for user to grant permissions and save the credentials
for future use by the sync system.

Usage:
    python scripts/setup_google_drive.py
"""

import os
import sys
import pickle
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OAuth scopes required for readonly access
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def setup_oauth():
    """Run OAuth setup flow and save credentials"""

    print("=" * 60)
    print("Google Drive OAuth Setup")
    print("=" * 60)
    print()

    # Get credentials path from environment
    credentials_path = os.path.expanduser(
        os.getenv(
            "GOOGLE_DRIVE_CREDENTIALS_PATH",
            "~/.config/rcsb_pdb_chatbot/google_drive_credentials.json"
        )
    )
    credentials_path = Path(credentials_path)

    # Check if credentials file exists
    if not credentials_path.exists():
        print("❌ ERROR: Credentials file not found!")
        print(f"Expected location: {credentials_path}")
        print()
        print("Please follow these steps:")
        print()
        print("1. Go to Google Cloud Console:")
        print("   https://console.cloud.google.com/")
        print()
        print("2. Create a new project (or select existing)")
        print()
        print("3. Enable the Google Drive API:")
        print("   - Go to 'APIs & Services' > 'Library'")
        print("   - Search for 'Google Drive API'")
        print("   - Click 'Enable'")
        print()
        print("4. Create OAuth credentials:")
        print("   - Go to 'APIs & Services' > 'Credentials'")
        print("   - Click 'Create Credentials' > 'OAuth client ID'")
        print("   - Configure OAuth consent screen if prompted")
        print("   - Choose 'Desktop app' as application type")
        print("   - Download the credentials JSON file")
        print()
        print(f"5. Save the credentials file as:")
        print(f"   {credentials_path}")
        print()
        print("6. Run this script again")
        print()
        return False

    print(f"✓ Found credentials file: {credentials_path}")
    print()

    # Get token path from environment (K8s-friendly, project-relative)
    token_path_str = os.getenv(
        "GOOGLE_DRIVE_TOKEN_PATH",
        "credentials/google_drive_token.pickle"
    )

    # Get project root
    project_root = Path(__file__).parent.parent

    # Support both absolute and relative paths
    if os.path.isabs(token_path_str):
        token_path = Path(os.path.expanduser(token_path_str))
    else:
        token_path = project_root / token_path_str

    # Check if token already exists
    if token_path.exists():
        print(f"⚠️  OAuth token already exists at: {token_path}")
        response = input("Do you want to re-authenticate? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled.")
            return True

    print("Starting OAuth flow...")
    print()
    print("🌐 Your browser will open automatically.")
    print("Please:")
    print("  1. Sign in with your Google account")
    print("  2. Click 'Allow' to grant access")
    print("  3. You should see 'The authentication flow has completed'")
    print("  4. Return to this terminal")
    print()
    input("Press ENTER to open browser and start authentication...")

    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            SCOPES
        )
        creds = flow.run_local_server(port=0)

        # Ensure token directory exists with secure permissions
        token_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Save credentials
        with open(token_path, 'wb') as token_file:
            pickle.dump(creds, token_file)

        # Set restrictive permissions (owner read/write only)
        token_path.chmod(0o600)

        print()
        print("=" * 60)
        print("✓ SUCCESS!")
        print("=" * 60)
        print(f"✓ OAuth token saved to: {token_path}")
        print("✓ Google Drive access granted")
        print()
        print("You can now run the sync script:")
        print("  python -m src.google_drive_sync.sync_manager")
        print()
        print("Or set up a cron job:")
        print("  See scripts/sync_google_drive.sh")
        print()
        return True

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR during authentication")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Common issues:")
        print("  - Browser didn't open: Check popup blockers")
        print("  - Access denied: Ensure OAuth consent screen is configured")
        print("  - Wrong redirect URI: Use 'Desktop app' type in Google Console")
        print()
        return False


def verify_setup():
    """Verify that OAuth setup was successful"""
    print("Verifying setup...")
    print()

    token_path = os.path.expanduser(
        os.getenv(
            "GOOGLE_DRIVE_TOKEN_PATH",
            "~/.config/rcsb_pdb_chatbot/google_drive_token.json"
        )
    )
    token_path = Path(token_path)

    if not token_path.exists():
        print("❌ Token file not found. Setup may have failed.")
        return False

    try:
        with open(token_path, 'rb') as token_file:
            creds = pickle.load(token_file)

        if creds and creds.valid:
            print("✓ OAuth token is valid")
            print()
            print("Setup complete! You can now sync from Google Drive.")
            return True
        else:
            print("⚠️  Token exists but may not be valid")
            return False
    except Exception as e:
        print(f"❌ Error verifying token: {e}")
        return False


def main():
    """Main setup process"""
    success = setup_oauth()

    if success:
        verify_setup()
    else:
        print("Setup failed. Please try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
