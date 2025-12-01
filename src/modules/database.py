"""Database manager for Bible Shorts Generator using SQLite"""
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, List, Any


class Database:
    """SQLite database manager for tracking videos and upload queue"""

    def __init__(self, db_path: str = "data/database.db"):
        self.db_path = Path(db_path)
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allow dict-like access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            conn.executescript("""
                -- Videos table
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    verse_id TEXT NOT NULL UNIQUE,
                    book TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    verse INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    duration REAL NOT NULL,

                    background_path TEXT,
                    audio_path TEXT,
                    timestamps_path TEXT,
                    subtitle_path TEXT,
                    final_path TEXT,

                    youtube_id TEXT,
                    youtube_url TEXT,
                    upload_date TIMESTAMP,

                    status TEXT NOT NULL DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Upload queue table
                CREATE TABLE IF NOT EXISTS upload_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    scheduled_time TIMESTAMP NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    FOREIGN KEY (video_id) REFERENCES videos(id)
                );

                -- Statistics table
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    videos_generated INTEGER DEFAULT 0,
                    videos_uploaded INTEGER DEFAULT 0,
                    total_duration REAL DEFAULT 0,
                    errors INTEGER DEFAULT 0
                );

                -- Progress tracking table (for sequential verse processing)
                CREATE TABLE IF NOT EXISTS progress (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    current_book TEXT,
                    current_chapter INTEGER,
                    current_verse INTEGER,
                    mode TEXT DEFAULT 'random',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Insert default progress row if not exists
                INSERT OR IGNORE INTO progress (id, mode) VALUES (1, 'random');

                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
                CREATE INDEX IF NOT EXISTS idx_videos_verse ON videos(book, chapter, verse);
                CREATE INDEX IF NOT EXISTS idx_queue_scheduled ON upload_queue(scheduled_time, status);
                CREATE INDEX IF NOT EXISTS idx_videos_retry ON videos(status, retry_count);
            """)

    def add_video(self, verse_data: Dict[str, Any]) -> int:
        """
        Add a new video record

        Args:
            verse_data: Dictionary containing verse information

        Returns:
            video_id: ID of newly created video record
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO videos (
                    verse_id, book, chapter, verse, text, word_count, duration, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                verse_data['id'],
                verse_data['book'],
                verse_data['chapter'],
                verse_data['verse'],
                verse_data['text'],
                verse_data['word_count'],
                verse_data['duration']
            ))
            return cursor.lastrowid

    def update_video_status(self, video_id: int, status: str):
        """Update video status"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE videos
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, video_id))

    def update_video_path(self, video_id: int, path_field: str, path_value: str):
        """Update a specific path field for a video"""
        valid_fields = [
            'background_path', 'audio_path', 'timestamps_path',
            'subtitle_path', 'final_path'
        ]
        if path_field not in valid_fields:
            raise ValueError(f"Invalid path field: {path_field}")

        with self.get_connection() as conn:
            conn.execute(f"""
                UPDATE videos
                SET {path_field} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (path_value, video_id))

    def update_video_upload(self, video_id: int, youtube_id: str, youtube_url: str):
        """Update video with YouTube upload information"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE videos
                SET youtube_id = ?,
                    youtube_url = ?,
                    upload_date = CURRENT_TIMESTAMP,
                    status = 'uploaded',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (youtube_id, youtube_url, video_id))

    def get_video(self, video_id: int) -> Optional[Dict[str, Any]]:
        """Get video by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def verse_exists(self, verse_id: str) -> bool:
        """Check if verse has already been generated"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM videos WHERE verse_id = ?",
                (verse_id,)
            )
            return cursor.fetchone()[0] > 0

    def get_ready_videos(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get videos ready for upload"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM videos
                WHERE status = 'ready'
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_next_to_upload(self) -> Optional[int]:
        """Get next video ID ready for upload"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id FROM videos
                WHERE status = 'ready'
                ORDER BY created_at ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return row[0] if row else None

    def add_to_upload_queue(self, video_id: int, scheduled_time: datetime):
        """Add video to upload queue"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO upload_queue (video_id, scheduled_time, status)
                VALUES (?, ?, 'pending')
            """, (video_id, scheduled_time))

    def update_queue_status(self, queue_id: int, status: str, error_message: str = None):
        """Update upload queue status"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE upload_queue
                SET status = ?, error_message = ?, retry_count = retry_count + 1
                WHERE id = ?
            """, (status, error_message, queue_id))

    def get_pending_uploads(self) -> List[Dict[str, Any]]:
        """Get pending uploads from queue"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT uq.*, v.*
                FROM upload_queue uq
                JOIN videos v ON uq.video_id = v.id
                WHERE uq.status = 'pending'
                    AND uq.scheduled_time <= CURRENT_TIMESTAMP
                ORDER BY uq.scheduled_time ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_statistics(self, date: str = None, **kwargs):
        """Update daily statistics"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        with self.get_connection() as conn:
            # Insert or update statistics
            fields = ', '.join([f"{k} = {k} + ?" for k in kwargs.keys()])
            values = list(kwargs.values())

            conn.execute(f"""
                INSERT INTO statistics (date, {', '.join(kwargs.keys())})
                VALUES (?, {', '.join(['?'] * len(kwargs))})
                ON CONFLICT(date) DO UPDATE SET {fields}
            """, [date] + values + values)

    def get_statistics(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get statistics for the last N days"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM statistics
                ORDER BY date DESC
                LIMIT ?
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

    def get_video_count_by_status(self) -> Dict[str, int]:
        """Get count of videos by status"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM videos
                GROUP BY status
            """)
            return {row['status']: row['count'] for row in cursor.fetchall()}

    def cleanup_old_queue_entries(self, days: int = 7):
        """Clean up old completed/failed queue entries"""
        with self.get_connection() as conn:
            conn.execute("""
                DELETE FROM upload_queue
                WHERE status IN ('uploaded', 'failed')
                    AND scheduled_time < datetime('now', ? || ' days')
            """, (f'-{days}',))

    # ========== Retry Logic Methods ==========

    def mark_video_failed(self, video_id: int, error_message: str):
        """Mark video as failed with error message"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE videos
                SET status = 'failed',
                    error_message = ?,
                    retry_count = retry_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (error_message, video_id))

    def get_failed_videos_for_retry(self, max_retry_count: int = 3) -> List[Dict[str, Any]]:
        """Get failed videos eligible for retry"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM videos
                WHERE status = 'failed'
                    AND retry_count < ?
                ORDER BY updated_at ASC
                LIMIT 10
            """, (max_retry_count,))
            return [dict(row) for row in cursor.fetchall()]

    def reset_video_for_retry(self, video_id: int):
        """Reset video status to pending for retry"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE videos
                SET status = 'pending',
                    error_message = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (video_id,))

    # ========== Progress Tracking Methods ==========

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress for sequential processing"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM progress WHERE id = 1")
            row = cursor.fetchone()
            return dict(row) if row else {'mode': 'random'}

    def set_progress(self, book: str, chapter: int, verse: int):
        """Update progress after processing a verse"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE progress
                SET current_book = ?,
                    current_chapter = ?,
                    current_verse = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (book, chapter, verse))

    def set_mode(self, mode: str):
        """Set processing mode (random or sequential)"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE progress
                SET mode = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (mode,))

    def get_total_verses_count(self) -> int:
        """Get total number of verses in database"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM videos")
            return cursor.fetchone()['count']

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get detailed processing statistics"""
        with self.get_connection() as conn:
            stats = {}

            # Count by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM videos
                GROUP BY status
            """)
            for row in cursor:
                stats[row['status']] = row['count']

            # Total and percentage
            total = sum(stats.values())
            stats['total'] = total

            # Retry statistics
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_failed,
                    SUM(CASE WHEN retry_count >= 3 THEN 1 ELSE 0 END) as permanently_failed
                FROM videos
                WHERE status = 'failed'
            """)
            row = cursor.fetchone()
            stats['total_failed'] = row['total_failed'] or 0
            stats['permanently_failed'] = row['permanently_failed'] or 0
            stats['retryable'] = stats['total_failed'] - stats['permanently_failed']

            return stats
