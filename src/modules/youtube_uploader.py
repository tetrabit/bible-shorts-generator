"""YouTube uploader using YouTube Data API v3"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from typing import Dict, Optional


class YouTubeUploader:
    """Uploads videos to YouTube using API v3"""

    def __init__(self, config):
        self.config = config
        self.youtube = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with YouTube API"""
        if not all([
            self.config.youtube_client_id,
            self.config.youtube_client_secret,
            self.config.youtube_refresh_token
        ]):
            raise ValueError(
                "YouTube credentials not found. "
                "Please run auth.py to authenticate."
            )

        creds = Credentials(
            None,
            refresh_token=self.config.youtube_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.config.youtube_client_id,
            client_secret=self.config.youtube_client_secret,
            scopes=['https://www.googleapis.com/auth/youtube.upload']
        )

        # Refresh token if expired
        if creds.expired or not creds.valid:
            creds.refresh(Request())

        self.youtube = build('youtube', 'v3', credentials=creds)
        print("YouTube authentication successful")

    def generate_title(self, verse_data: Dict) -> str:
        """Generate video title from template"""
        first_words = " ".join(verse_data['text'].split()[:5])
        return self.config.youtube['title_template'].format(
            verse_ref=verse_data['reference'],
            first_words=first_words
        )

    def generate_description(self, verse_data: Dict) -> str:
        """Generate video description from template"""
        return self.config.youtube['description_template'].format(
            verse_text=verse_data['text'],
            verse_ref=verse_data['reference'],
            bible_version=self.config.bible['version']
        )

    def upload(
        self,
        video_path: str,
        verse_data: Dict,
        privacy: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Upload video to YouTube

        Args:
            video_path: Path to video file
            verse_data: Dictionary with verse information
            privacy: Privacy status (public, private, unlisted)

        Returns:
            dict: Upload result with id and url
        """
        print(f"Uploading video: {video_path}")

        # Generate metadata
        title = self.generate_title(verse_data)
        description = self.generate_description(verse_data)
        privacy_status = privacy or self.config.youtube['privacy']

        # Prepare request body
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': self.config.youtube['tags'],
                'categoryId': self.config.youtube['category_id']
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }

        # Upload video
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024 * 1024  # 1MB chunks
        )

        request = self.youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        print("Starting upload...")
        response = None
        last_progress = 0

        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                if progress != last_progress:
                    print(f"Upload progress: {progress}%")
                    last_progress = progress

        video_id = response['id']
        video_url = f"https://youtube.com/shorts/{video_id}"

        print(f"Upload complete!")
        print(f"Video ID: {video_id}")
        print(f"URL: {video_url}")

        return {
            'id': video_id,
            'url': video_url,
            'title': title
        }

    def update_video(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list] = None
    ):
        """Update video metadata"""
        # Get current video details
        video = self.youtube.videos().list(
            part='snippet',
            id=video_id
        ).execute()

        if not video['items']:
            raise ValueError(f"Video not found: {video_id}")

        snippet = video['items'][0]['snippet']

        # Update fields
        if title:
            snippet['title'] = title
        if description:
            snippet['description'] = description
        if tags:
            snippet['tags'] = tags

        # Update video
        self.youtube.videos().update(
            part='snippet',
            body={
                'id': video_id,
                'snippet': snippet
            }
        ).execute()

        print(f"Video {video_id} updated successfully")

    def delete_video(self, video_id: str):
        """Delete a video"""
        self.youtube.videos().delete(id=video_id).execute()
        print(f"Video {video_id} deleted successfully")
