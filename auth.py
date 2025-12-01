#!/usr/bin/env python3
"""
YouTube API Authentication Script
Run this once to authenticate and get refresh token
"""
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path

# YouTube upload scope
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def authenticate():
    """Run OAuth flow to get credentials"""

    # Check for client secrets file
    secrets_file = 'client_secrets.json'
    if not Path(secrets_file).exists():
        print("ERROR: client_secrets.json not found!")
        print("\nPlease follow these steps:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable 'YouTube Data API v3'")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download the credentials file as 'client_secrets.json'")
        print("6. Place it in this directory")
        return

    print("Starting YouTube authentication...")
    print("A browser window will open for authorization.\n")

    # Run OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        secrets_file,
        SCOPES
    )

    credentials = flow.run_local_server(
        port=8080,
        prompt='consent',
        authorization_prompt_message='Please visit this URL: {url}'
    )

    print("\nAuthentication successful!")

    # Load or create .env file
    env_file = Path('.env')
    env_lines = []

    if env_file.exists():
        with open(env_file) as f:
            env_lines = [line for line in f.readlines()
                        if not line.startswith('YOUTUBE_')]

    # Add YouTube credentials
    env_lines.append(f"\n# YouTube API Credentials\n")
    env_lines.append(f"YOUTUBE_CLIENT_ID={credentials.client_id}\n")
    env_lines.append(f"YOUTUBE_CLIENT_SECRET={credentials.client_secret}\n")
    env_lines.append(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}\n")

    # Write .env file
    with open('.env', 'w') as f:
        f.writelines(env_lines)

    print("\nCredentials saved to .env file")
    print("You can now use the Bible Shorts Generator!")


if __name__ == "__main__":
    authenticate()
