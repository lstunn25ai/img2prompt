# GitHub Portainer GitOps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an image-based GitHub deployment path without changing the existing server-source Compose path.

**Architecture:** `docker-compose.yml` remains the current bind-mount deployment. `gh_docker-compose.yml` runs an immutable image from GHCR and mounts only persistent Obsidian data. GitHub Actions tests pull requests, builds tagged images after merges to `main`, and optionally calls a Portainer webhook after an image is available.

**Tech Stack:** Docker, Docker Compose, GitHub Actions, GitHub Container Registry, Portainer, Python unittest.

## Global Constraints

- Keep `docker-compose.yml` compatible with the existing server bind-mount deployment.
- Do not publish secrets, host paths, private network names, bot tokens, or Portainer webhook URLs.
- Do not configure Portainer or GitHub Secrets automatically.
- The production Stack follows `main`; pull-request branches run CI only.
- The GitHub image deployment must not mount `${APP_PATH}` to `/app`.

---

### Task 1: Contract tests for the GitHub deployment path

**Files:**
- Modify: `tests/test_source_contract.py`
- Create: `gh_docker-compose.yml`, `Dockerfile`, `.dockerignore`

- [ ] Write tests requiring a prebuilt `${BOT_IMAGE}:${IMAGE_TAG}`, persistent vault mounts, and no `${APP_PATH}:/app` in `gh_docker-compose.yml`.
- [ ] Run `py -B -m unittest tests.test_source_contract` and verify it fails because the GitHub deployment files do not exist.
- [ ] Add the Docker build and GitHub Compose files.
- [ ] Run the same test and the full suite until they pass.

### Task 2: GitHub Actions delivery pipeline

**Files:**
- Create: `.github/workflows/ci-ghcr.yml`
- Modify: `tests/test_source_contract.py`

- [ ] Write tests requiring PR verification, `main` image publication, immutable SHA tags, and an optional `PORTAINER_WEBHOOK_URL` step.
- [ ] Verify the tests fail before the workflow exists.
- [ ] Add a workflow that runs tests and Compose validation on PRs, publishes a GHCR image only from `main`, and invokes the webhook only when its secret is configured.
- [ ] Verify workflow structure with static tests and validate both Compose files with `.env.example`.

### Task 3: User-facing deployment documentation

**Files:**
- Modify: `README.md`, `.env.example`
- Modify: `tests/test_source_contract.py`

- [ ] Write tests requiring README coverage of the two Compose variants and GitOps setup.
- [ ] Verify the tests fail before the documentation is added.
- [ ] Document first migration, required Portainer variables, GitOps webhook toggles, PR-to-main workflow, and rollback through immutable image tags.
- [ ] Verify the full suite and public-safety scan pass.

### Task 4: Reusable GitHub skill handoff

**Files:**
- Modify: `C:/Users/lstun/.agents/skills/github/SKILL.md`
- Create: `C:/Users/lstun/.agents/skills/github/references/portainer-gitops-flow.mmd`

- [ ] Record the baseline gap: the current skill contains no Portainer Git deployment handoff or GitOps checklist.
- [ ] Add a conditional Docker/Portainer completion section that produces the exact user handoff, never exposes values, and does not enable GitOps without approval.
- [ ] Add the Mermaid flow from feature branch through PR, `main`, GHCR image, and Portainer webhook.
- [ ] Verify the required headings, environment-variable guidance, guardrails, and graph source are retrievable from the updated skill.

### Task 5: Verification and handoff

**Files:**
- Verify: all changed files

- [ ] Run all unit tests, syntax validation, both Compose validations, and a public-safety scan.
- [ ] Review the exact changed-file list; do not stage `.env`, `AGENTS.md`, local skills, or any secret.
- [ ] Report the branch, files, verification evidence, and manual Portainer migration sequence.
