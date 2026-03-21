import unittest
from unittest.mock import patch, mock_open

from maigret.settings import Settings


class TestSettings(unittest.TestCase):
    @patch('json.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_settings_cascade_and_override(self, mock_file, mock_json_load):
        file1_data = {"timeout": 10, "retries_count": 3, "proxy_url": "http://proxy1"}
        file2_data = {"timeout": 20, "recursive_search": True}
        file3_data = {"proxy_url": "http://proxy3", "print_not_found": False}

        mock_json_load.side_effect = [file1_data, file2_data, file3_data]

        settings = Settings()
        paths = ['file1.json', 'file2.json', 'file3.json']

        was_inited, msg = settings.load(paths)

        self.assertTrue(was_inited)
        self.assertEqual(settings.retries_count, 3)
        self.assertEqual(settings.timeout, 20)
        self.assertTrue(settings.recursive_search)
        self.assertEqual(settings.proxy_url, "http://proxy3")
        self.assertFalse(settings.print_not_found)

    @patch('builtins.open')
    def test_settings_file_not_found(self, mock_open_func):
        mock_open_func.side_effect = FileNotFoundError()

        settings = Settings()
        paths = ['nonexistent.json']

        was_inited, msg = settings.load(paths)

        self.assertFalse(was_inited)
        self.assertIn('None of the default settings files found', msg)

    @patch('json.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_settings_invalid_json(self, mock_file, mock_json_load):
        mock_json_load.side_effect = ValueError("Expecting value")

        settings = Settings()
        paths = ['invalid.json']

        was_inited, msg = settings.load(paths)

        self.assertFalse(was_inited)
        self.assertIsInstance(msg, ValueError)
        self.assertIn('Problem with parsing json contents', str(msg))
