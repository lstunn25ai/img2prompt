import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GH_COMPOSE_PATH = ROOT / "gh_docker-compose.yml"
DOCKERFILE_PATH = ROOT / "Dockerfile"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci-ghcr.yml"
README_PATH = ROOT / "README.md"


class GitHubDeploymentContractTests(unittest.TestCase):
    def test_github_compose_uses_a_prebuilt_image_without_mounting_source_code(self):
        self.assertTrue(GH_COMPOSE_PATH.is_file())
        gh_compose = GH_COMPOSE_PATH.read_text(encoding="utf-8")

        self.assertIn("image: ${BOT_IMAGE}:${IMAGE_TAG}", gh_compose)
        self.assertIn("pull_policy: always", gh_compose)
        self.assertNotIn("${APP_PATH}:/app", gh_compose)
        self.assertIn("${SAVE_PATH}:${SAVE_PATH}", gh_compose)
        self.assertIn("${ATTACHMENTS_PATH}:${ATTACHMENTS_PATH}", gh_compose)
        self.assertIn("BOT_TOKEN=${BOT_TOKEN}", gh_compose)

    def test_dockerfile_bakes_runtime_source_into_the_image(self):
        self.assertTrue(DOCKERFILE_PATH.is_file())
        dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")

        self.assertIn("FROM python:3.11-slim", dockerfile)
        self.assertIn("COPY requirements.txt", dockerfile)
        self.assertIn("COPY bot.py preview_assets.py proxy_routing.py", dockerfile)
        self.assertIn('CMD ["python", "-u", "bot.py"]', dockerfile)

    def test_github_actions_tests_prs_and_deploys_only_main_images(self):
        self.assertTrue(WORKFLOW_PATH.is_file())
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("pull_request:", workflow)
        self.assertIn("branches: [main]", workflow)
        self.assertIn("ghcr.io/${{ github.repository }}", workflow)
        self.assertIn("sha-${{ github.sha }}", workflow)
        self.assertIn("PORTAINER_WEBHOOK_URL", workflow)

    def test_readme_distinguishes_server_and_github_compose_paths(self):
        readme = README_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("docker-compose.yml", readme)
        self.assertIn("gh_docker-compose.yml", readme)
        self.assertIn("GitOps", readme)


if __name__ == "__main__":
    unittest.main()
