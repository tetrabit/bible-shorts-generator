"""Bible verse selector with duration filtering"""
import pythonbible as bible
import random
from typing import Optional, Dict, Any
from .timing_analyzer import TimingAnalyzer
from .database import Database


class VerseSelector:
    """Selects Bible verses that meet duration criteria"""

    def __init__(self, config, db: Database):
        self.config = config
        self.db = db
        self.timing = TimingAnalyzer(config)

        # Get allowed books
        self.allowed_books = self._get_allowed_books()

    def _get_allowed_books(self) -> list:
        """Get list of allowed Bible book enums"""
        # Normalize names to the enum naming style used by pythonbible (UPPER_CASE_WITH_UNDERSCORES)
        normalize = lambda name: name.replace(" ", "_").upper()
        allowed_names = {normalize(name) for name in self.config.bible['books']}
        excluded_names = {normalize(name) for name in self.config.bible.get('exclude_books', [])}

        # Convert book names to pythonbible Book enums
        allowed_books = []
        for book_enum in bible.Book:
            book_name = book_enum.name
            if book_name in allowed_names and book_name not in excluded_names:
                allowed_books.append(book_enum)

        # If nothing matched, default to all books rather than failing
        if not allowed_books:
            allowed_books = [b for b in bible.Book if b.name not in excluded_names]

        return allowed_books

    def select_verse(self) -> Optional[Dict[str, Any]]:
        """
        Select a verse that meets criteria (random or sequential based on config)

        Returns:
            dict: Verse data including text, reference, duration
            None: If no suitable verse found after max attempts
        """
        # Check mode from database
        progress = self.db.get_progress()
        mode = progress.get('mode', 'random')

        if mode == 'sequential':
            return self._select_sequential_verse()
        else:
            return self._select_random_verse()

    def _select_random_verse(self) -> Optional[Dict[str, Any]]:
        """Select a random verse that meets criteria"""
        max_attempts = 200
        min_words = self.config.bible['min_words']
        max_words = self.config.bible['max_words']

        for attempt in range(max_attempts):
            try:
                # Select random book
                book = random.choice(self.allowed_books)

                # Get a random verse from this book
                verse_id = self._get_random_verse_id(book)
                if not verse_id:
                    continue

                # Get verse text
                text = bible.get_verse_text(verse_id, version=bible.Version.KING_JAMES)
                if not text:
                    continue

                # Clean the text
                text = text.strip()

                # Check word count
                word_count = len(text.split())
                if not (min_words <= word_count <= max_words):
                    continue

                # Check duration
                duration = self.timing.calculate_duration(text)
                if duration > self.config.video['max_duration']:
                    continue

                # Parse verse ID
                verse_info = self._parse_verse_id(verse_id)

                # Create verse ID string
                verse_id_str = f"{verse_info['book']}_{verse_info['chapter']}_{verse_info['verse']}"

                # Check if already generated
                if self.db.verse_exists(verse_id_str):
                    continue

                # Create verse data
                verse_data = {
                    'id': verse_id_str,
                    'book': verse_info['book'],
                    'chapter': verse_info['chapter'],
                    'verse': verse_info['verse'],
                    'reference': f"{verse_info['book']} {verse_info['chapter']}:{verse_info['verse']}",
                    'text': text,
                    'word_count': word_count,
                    'duration': duration
                }

                return verse_data

            except Exception as e:
                # Skip this verse and try another
                continue

        return None

    def _get_random_verse_id(self, book: bible.Book) -> Optional[int]:
        """
        Get a random verse ID from a book

        Args:
            book: Bible book enum

        Returns:
            verse_id: Random verse ID from the book
        """
        try:
            # Get all verse IDs for this book
            # pythonbible uses verse IDs as integers
            # We'll generate a random chapter and verse

            # Get number of chapters in book (approximation)
            # This is simplified - in production you'd want exact chapter counts
            max_chapter = self._get_chapter_count(book)
            chapter = random.randint(1, max_chapter)

            # Get random verse (most chapters have at least 10 verses)
            max_verse = random.randint(10, 30)
            verse = random.randint(1, max_verse)

            # Create verse reference
            references = bible.get_references(f"{book.title} {chapter}:{verse}")
            if references:
                # Get first verse ID
                verse_ids = list(bible.convert_references_to_verse_ids(references))
                if verse_ids:
                    return verse_ids[0]

        except Exception:
            pass

        return None

    def _get_chapter_count(self, book: bible.Book) -> int:
        """Get approximate chapter count for a book"""
        # Simplified chapter counts for common books
        chapter_counts = {
            'Psalms': 150,
            'Proverbs': 31,
            'John': 21,
            'Matthew': 28,
            'Philippians': 4,
            'Romans': 16,
            'Genesis': 50,
            'Exodus': 40,
            'Isaiah': 66,
            'Jeremiah': 52
        }
        return chapter_counts.get(book.name, 20)  # Default to 20

    def _parse_verse_id(self, verse_id: int) -> Dict[str, Any]:
        """
        Parse verse ID to get book, chapter, verse

        Args:
            verse_id: Integer verse ID

        Returns:
            dict: Parsed verse information
        """
        # Get verse references
        verse_ids = [verse_id]
        reference = bible.format_scripture_references(
            bible.convert_verse_ids_to_references(verse_ids)
        )

        # This is a simplified parser
        # pythonbible should provide better methods
        parts = reference.split()
        book_name = parts[0]
        chapter_verse = parts[1] if len(parts) > 1 else "1:1"
        chapter, verse = chapter_verse.split(':')

        return {
            'book': book_name,
            'chapter': int(chapter),
            'verse': int(verse)
        }

    def _select_sequential_verse(self) -> Optional[Dict[str, Any]]:
        """
        Select the next verse sequentially from allowed books

        Returns:
            dict: Verse data or None if no more verses
        """
        progress = self.db.get_progress()
        current_book = progress.get('current_book')
        current_chapter = progress.get('current_chapter', 1)
        current_verse = progress.get('current_verse', 0)

        # If no current book, start with first allowed book
        if not current_book:
            current_book = self.allowed_books[0].name
            current_chapter = 1
            current_verse = 0

        # Find the book in allowed books
        book_names = [b.name for b in self.allowed_books]
        if current_book not in book_names:
            # Book no longer in allowed list, start fresh
            current_book = self.allowed_books[0].name
            current_chapter = 1
            current_verse = 0

        max_attempts = 100
        min_words = self.config.bible['min_words']
        max_words = self.config.bible['max_words']

        for attempt in range(max_attempts):
            try:
                # Try next verse
                next_verse = current_verse + 1

                # Try to get this verse
                reference = f"{current_book} {current_chapter}:{next_verse}"
                verse_ids = bible.convert_references_to_verse_ids(
                    bible.get_references(reference)
                )

                if not verse_ids:
                    # No more verses in this chapter, move to next chapter
                    current_chapter += 1
                    current_verse = 0

                    # Check if chapter exists
                    reference = f"{current_book} {current_chapter}:1"
                    verse_ids = bible.convert_references_to_verse_ids(
                        bible.get_references(reference)
                    )

                    if not verse_ids:
                        # No more chapters in this book, move to next book
                        book_idx = book_names.index(current_book)
                        if book_idx + 1 >= len(book_names):
                            # We've gone through all books!
                            return None

                        current_book = book_names[book_idx + 1]
                        current_chapter = 1
                        current_verse = 0
                        continue

                    next_verse = 1

                # Get verse text
                verse_id = list(verse_ids)[0]
                text = bible.get_verse_text(verse_id, version=bible.Version.KING_JAMES)

                if not text:
                    current_verse = next_verse
                    continue

                text = text.strip()

                # Check word count
                word_count = len(text.split())
                if not (min_words <= word_count <= max_words):
                    current_verse = next_verse
                    continue

                # Check duration
                duration = self.timing.calculate_duration(text)
                if duration > self.config.video['max_duration']:
                    current_verse = next_verse
                    continue

                # Create verse ID string
                verse_id_str = f"{current_book}_{current_chapter}_{next_verse}"

                # Check if already generated
                if self.db.verse_exists(verse_id_str):
                    current_verse = next_verse
                    continue

                # Found a good verse! Update progress
                self.db.set_progress(current_book, current_chapter, next_verse)

                # Create verse data
                verse_data = {
                    'id': verse_id_str,
                    'book': current_book,
                    'chapter': current_chapter,
                    'verse': next_verse,
                    'reference': f"{current_book} {current_chapter}:{next_verse}",
                    'text': text,
                    'word_count': word_count,
                    'duration': duration
                }

                return verse_data

            except Exception as e:
                # Skip this verse
                current_verse = next_verse
                continue

        return None
