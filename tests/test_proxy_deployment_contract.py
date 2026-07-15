import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProxyDeploymentContractTests(unittest.TestCase):
    def test_bot_exposes_admin_only_manual_gateway_switch(self):
        source = (ROOT / "bot.py").read_text(encoding="utf-8-sig")

        self.assertIn('"🔄 Переключить шлюз"', source)
        self.assertIn("async def manual_proxy_switch", source)
        self.assertIn("PRIMARY_PROXY_URL", source)
        self.assertIn("RESERVE_PROXY_URL", source)

    def test_both_compose_files_pass_primary_and_reserve_proxy_variables(self):
        for compose_name in ("docker-compose.yml", "gh_docker-compose.yml"):
            compose = (ROOT / compose_name).read_text(encoding="utf-8")
            self.assertIn("PRIMARY_PROXY_URL=${PRIMARY_PROXY_URL:-}", compose)
            self.assertIn("RESERVE_PROXY_URL=${RESERVE_PROXY_URL:-}", compose)

    def test_public_example_and_readme_document_proxy_switch_without_values(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("PRIMARY_PROXY_URL=http://primary-proxy:8080", env_example)
        self.assertIn("RESERVE_PROXY_URL=http://reserve-proxy:8080", env_example)
        self.assertIn("Переключить шлюз", readme)


if __name__ == "__main__":
    unittest.main()
