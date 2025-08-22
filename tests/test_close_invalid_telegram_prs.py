"""Tests for the close_invalid_telegram_prs utility."""

import unittest
import sys
import os

# Add the utils directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

from close_invalid_telegram_prs import is_invalid_telegram_pr


class TestCloseInvalidTelegramPRs(unittest.TestCase):
    """Test cases for the invalid Telegram PR detection."""
    
    def test_valid_invalid_telegram_pr_titles(self):
        """Test that valid invalid Telegram PR titles are correctly identified."""
        valid_titles = [
            "Invalid result https://t.me/someuser",
            "invalid result https://t.me/channel123", 
            "Invalid Result https://t.me/bot_name",
            "INVALID RESULT https://t.me/test",
            "Invalid result https://t.me/user/123",
            "Invalid result https://t.me/s/channel_name",
        ]
        
        for title in valid_titles:
            with self.subTest(title=title):
                self.assertTrue(is_invalid_telegram_pr(title), 
                               f"Title should be identified as invalid: {title}")
    
    def test_invalid_telegram_pr_titles_not_matching(self):
        """Test that non-matching titles are correctly rejected."""
        invalid_titles = [
            "Valid result https://t.me/someuser",  # "Valid" instead of "Invalid"
            "Invalid results https://t.me/someuser",  # "results" instead of "result"
            "Invalid result http://t.me/someuser",  # "http" instead of "https"
            "Invalid result https://telegram.me/someuser",  # Wrong domain
            "Fix invalid result https://t.me/someuser",  # Extra words before
            "Invalid result for https://t.me/someuser",  # Extra words in between
            "Added telegram site",  # Completely different
            "Fix false positives",  # Unrelated
            "",  # Empty title
            "Invalid result",  # Missing URL
            "https://t.me/someuser",  # Missing "Invalid result"
        ]
        
        for title in invalid_titles:
            with self.subTest(title=title):
                self.assertFalse(is_invalid_telegram_pr(title), 
                                f"Title should NOT be identified as invalid: {title}")
    
    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        titles_with_whitespace = [
            "  Invalid result https://t.me/someuser  ",  # Leading/trailing spaces
            "\tInvalid result https://t.me/someuser\t",  # Tabs
            "Invalid\tresult\thttps://t.me/someuser",  # Tabs between words
            "Invalid  result  https://t.me/someuser",  # Multiple spaces
        ]
        
        for title in titles_with_whitespace:
            with self.subTest(title=title):
                self.assertTrue(is_invalid_telegram_pr(title), 
                               f"Title with whitespace should be identified: {title}")
    
    def test_case_insensitive(self):
        """Test that the pattern matching is case insensitive."""
        case_variations = [
            "invalid result https://t.me/someuser",
            "Invalid Result https://t.me/someuser", 
            "INVALID RESULT https://t.me/someuser",
            "Invalid result https://T.ME/someuser",
            "iNvAlId ReSuLt https://t.me/someuser",
        ]
        
        for title in case_variations:
            with self.subTest(title=title):
                self.assertTrue(is_invalid_telegram_pr(title), 
                               f"Case variation should be identified: {title}")


if __name__ == '__main__':
    unittest.main()