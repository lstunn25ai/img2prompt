import ast
import unittest
from pathlib import Path


BOT_PATH = Path(__file__).resolve().parents[1] / "bot.py"


class ProxyImportContractTests(unittest.TestCase):
    def test_bot_imports_every_proxy_routing_symbol_it_uses(self):
        tree = ast.parse(BOT_PATH.read_text(encoding="utf-8-sig"))
        imported_names = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "proxy_routing"
            for alias in node.names
        }

        self.assertTrue(
            {
                "build_proxy_endpoints",
                "load_proxy_index",
                "next_proxy_index",
                "save_proxy_index",
            }.issubset(imported_names)
        )


if __name__ == "__main__":
    unittest.main()
