import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RussianSourceEncodingTests(unittest.TestCase):
    def test_bot_and_proxy_router_have_readable_russian_text(self):
        bot_source = (ROOT / "bot.py").read_text(encoding="utf-8-sig")
        proxy_source = (ROOT / "proxy_routing.py").read_text(encoding="utf-8-sig")

        self.assertIn("Резервный шлюз не задан", bot_source)
        self.assertIn("Основной", proxy_source)
        self.assertNotIn("Р Р", bot_source)
        self.assertNotIn("Р Р", proxy_source)


if __name__ == "__main__":
    unittest.main()
