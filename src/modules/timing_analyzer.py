"""Timing analyzer for estimating verse duration"""


class TimingAnalyzer:
    """Analyzes text to estimate speaking duration"""

    def __init__(self, config):
        self.config = config
        self.speaking_rate = config.text['speaking_rate']  # words per second
        self.max_duration = config.video['max_duration']  # seconds

    def calculate_duration(self, text: str) -> float:
        """
        Calculate estimated duration for speaking the text

        Args:
            text: Text to analyze

        Returns:
            duration: Estimated duration in seconds
        """
        words = text.split()
        word_count = len(words)
        duration = word_count / self.speaking_rate
        return round(duration, 2)

    def get_word_count(self, text: str) -> int:
        """Get word count of text"""
        return len(text.split())

    def is_within_duration(self, text: str) -> bool:
        """Check if text fits within max duration"""
        duration = self.calculate_duration(text)
        return duration <= self.max_duration

    def get_max_words(self) -> int:
        """Get maximum words for duration limit"""
        return int(self.max_duration * self.speaking_rate)

    def analyze_verse(self, verse_text: str) -> dict:
        """
        Analyze verse for timing information

        Args:
            verse_text: Verse text to analyze

        Returns:
            dict: Analysis results with word_count, duration, fits_duration
        """
        word_count = self.get_word_count(verse_text)
        duration = self.calculate_duration(verse_text)
        fits_duration = duration <= self.max_duration

        return {
            'word_count': word_count,
            'duration': duration,
            'fits_duration': fits_duration,
            'max_duration': self.max_duration,
            'max_words': self.get_max_words()
        }
