import unittest
from pathlib import Path


README_PATH = Path(__file__).resolve().parents[1] / "README.md"


class ReadmeEncodingTests(unittest.TestCase):
    def test_readme_is_utf8_without_bom_and_contains_readable_russian_heading(self):
        content = README_PATH.read_bytes()

        self.assertFalse(content.startswith(b"\xef\xbb\xbf"))
        text = content.decode("utf-8")
        self.assertIn("Ручное переключение шлюза", text)
        self.assertNotIn("РЎР", text)


if __name__ == "__main__":
    unittest.main()
