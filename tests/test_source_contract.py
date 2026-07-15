import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOT_PATH = ROOT / "bot.py"
COMPOSE_PATH = ROOT / "docker-compose.yml"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
GITIGNORE_PATH = ROOT / ".gitignore"


class SourceContractTests(unittest.TestCase):
    def test_bot_has_no_outbound_media_copy_or_forward_calls(self):
        forbidden = {
            "answer_document",
            "answer_photo",
            "copy_message",
            "copy_to",
            "forward",
            "forward_message",
            "reply_document",
            "reply_photo",
            "send_document",
            "send_media_group",
            "send_photo",
        }
        tree = ast.parse(BOT_PATH.read_text(encoding="utf-8-sig"))
        used_attributes = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }

        self.assertEqual(set(), forbidden & used_attributes)

    def test_bot_integrates_preview_creation_and_markdown_rendering(self):
        source = BOT_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("create_preview_asset", source)
        self.assertIn("save_preview_asset", source)
        self.assertIn("render_attachment_markdown", source)
        self.assertIn("ATTACHMENTS_PATH", source)

    def test_public_configuration_uses_environment_variables(self):
        bot_source = BOT_PATH.read_text(encoding="utf-8-sig")
        compose = COMPOSE_PATH.read_text(encoding="utf-8")
        env_example = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")

        self.assertNotIn("/srv/dev-disk-by-uuid-", bot_source)
        self.assertNotIn("/srv/dev-disk-by-uuid-", compose)
        self.assertNotRegex(bot_source, r"ADMIN_ID\s*=\s*\d+")
        self.assertIn('ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip())', bot_source)
        self.assertIn("APP_PATH=${APP_PATH}", compose)
        self.assertIn("ATTACHMENTS_PATH=${ATTACHMENTS_PATH}", compose)
        self.assertIn("${ATTACHMENTS_PATH}:${ATTACHMENTS_PATH}", compose)
        self.assertIn("ADMIN_ID=replace_with_your_telegram_user_id", env_example)
        self.assertIn("/srv/dev-disk-by-uuid-<disk-uuid>/", env_example)

    def test_public_repository_ignores_local_instructions_and_agent_artifacts(self):
        gitignore = GITIGNORE_PATH.read_text(encoding="utf-8")

        self.assertIn("AGENTS.md", gitignore)
        self.assertIn(".codex/", gitignore)
        self.assertIn(".claude/", gitignore)
        self.assertIn("ruflo/", gitignore)


if __name__ == "__main__":
    unittest.main()
