# img2prompt

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white) ![aiogram](https://img.shields.io/badge/aiogram-Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

Telegram-Р±РѕС‚ СЂР°СЃРїРѕР·РЅР°С‘С‚ С‚РµРєСЃС‚ РЅР° С„РѕС‚Рѕ Рё СЃРѕС…СЂР°РЅСЏРµС‚ Markdown-Р·Р°РјРµС‚РєРё СЃ JPEG-РїСЂРµРІСЊСЋ РґР»СЏ Obsidian. Р’ Telegram РѕРЅ РѕС‚РІРµС‡Р°РµС‚ С‚РѕР»СЊРєРѕ С‚РµРєСЃС‚РѕРј: Р±РµР· СЌС…Рѕ, РєРѕРїРёСЂРѕРІР°РЅРёСЏ Рё РїРµСЂРµСЃС‹Р»РєРё РјРµРґРёР°.

## РЎС‚СЂСѓРєС‚СѓСЂР°

```text
.
в”њв”Ђв”Ђ Dockerfile                         # РћР±СЂР°Р· Р±РѕС‚Р° РґР»СЏ GitHub/GHCR-РїРѕСЃС‚Р°РІРєРё
в”њв”Ђв”Ђ docker-compose.yml                 # РЎРµСЂРІРµСЂРЅС‹Р№ Р·Р°РїСѓСЃРє РёР· APP_PATH
в”њв”Ђв”Ђ gh_docker-compose.yml              # Р—Р°РїСѓСЃРє РіРѕС‚РѕРІРѕРіРѕ РѕР±СЂР°Р·Р° РёР· GHCR
в”њв”Ђв”Ђ .github/workflows/ci-ghcr.yml      # PR-РїСЂРѕРІРµСЂРєРё Рё РїСѓР±Р»РёРєР°С†РёСЏ РѕР±СЂР°Р·Р° main
в”њв”Ђв”Ђ bot.py                             # РҐРµРЅРґР»РµСЂС‹, OCR Рё СЃРѕС…СЂР°РЅРµРЅРёРµ Р·Р°РјРµС‚РѕРє
в”њв”Ђв”Ђ preview_assets.py                  # JPEG-РїСЂРµРІСЊСЋ Рё MD5-РґРµРґСѓРїР»РёРєР°С†РёСЏ
в”њв”Ђв”Ђ requirements.txt
в””в”Ђв”Ђ tests/
```

## Р’РѕР·РјРѕР¶РЅРѕСЃС‚Рё

- OCR С„РѕС‚Рѕ, РґРѕРєСѓРјРµРЅС‚РѕРІ-РёР·РѕР±СЂР°Р¶РµРЅРёР№ Рё Р°Р»СЊР±РѕРјРѕРІ С‡РµСЂРµР· OpenRouter.
- Obsidian Markdown, EXIF-РєРѕСЂСЂРµРєС†РёСЏ, РїСЂРѕР·СЂР°С‡РЅС‹Рµ PNG Рё JPEG-РїСЂРµРІСЊСЋ РґРѕ 300 px.
- РћС‚РІРµС‚С‹ Telegram С‚РѕР»СЊРєРѕ С‚РµРєСЃС‚РѕРј; СЂРµРіСЂРµСЃСЃРёРѕРЅРЅС‹Р№ С‚РµСЃС‚ Р·Р°РїСЂРµС‰Р°РµС‚ РёСЃС…РѕРґСЏС‰РёРµ РјРµРґРёР°, copy Рё forward.

## РђСЂС…РёС‚РµРєС‚СѓСЂР°

```mermaid
flowchart LR
    U[Telegram] --> B[aiogram bot]
    B --> O[OpenRouter OCR]
    O --> N[Obsidian Markdown]
    O --> A[JPEG preview]
    N --> V[(Obsidian Vault)]
    A --> V
```

## Р”РІР° РІР°СЂРёР°РЅС‚Р° Docker Compose

### `docker-compose.yml` вЂ” Р·Р°РїСѓСЃРє РёР· СЃРµСЂРІРµСЂРЅРѕР№ РїР°РїРєРё

Р­С‚РѕС‚ РІР°СЂРёР°РЅС‚ СЃРѕС…СЂР°РЅСЏРµС‚ РёСЃС…РѕРґРЅСѓСЋ СЃС…РµРјСѓ: `${APP_PATH}` РјРѕРЅС‚РёСЂСѓРµС‚СЃСЏ РІ `/app`, Р° РєРѕРЅС‚РµР№РЅРµСЂ Р·Р°РїСѓСЃРєР°РµС‚ РєРѕРґ РёР· РїР°РїРєРё РїСЂРѕРµРєС‚Р° РЅР° СЃРµСЂРІРµСЂРµ. РСЃРїРѕР»СЊР·СѓР№С‚Рµ РµРіРѕ РґР»СЏ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РµРіРѕ Р»РѕРєР°Р»СЊРЅРѕРіРѕ Stack РёР»Рё СЂСѓС‡РЅРѕР№ СЂР°Р·СЂР°Р±РѕС‚РєРё РЅР° СЃРµСЂРІРµСЂРµ.

РџРѕСЃР»Рµ РёР·РјРµРЅРµРЅРёСЏ РєРѕРґР° РІ `APP_PATH` РЅСѓР¶РµРЅ restart/redeploy РєРѕРЅС‚РµР№РЅРµСЂР°. Push РІ GitHub СЃР°Рј РїРѕ СЃРµР±Рµ СЌС‚РѕС‚ РєРѕРґ РЅРµ Р·Р°РјРµРЅСЏРµС‚.

### `gh_docker-compose.yml` вЂ” Р·Р°РїСѓСЃРє РєРѕРґР° РёР· GitHub

Р­С‚РѕС‚ РІР°СЂРёР°РЅС‚ **РЅРµ РјРѕРЅС‚РёСЂСѓРµС‚ `${APP_PATH}`**. GitHub Actions СЃРѕР±РёСЂР°РµС‚ `Dockerfile`, РїСѓР±Р»РёРєСѓРµС‚ РѕР±СЂР°Р· РІ GHCR, Р° Portainer Р·Р°РїСѓСЃРєР°РµС‚ `${BOT_IMAGE}:${IMAGE_TAG}`. РќР° СЃРµСЂРІРµСЂРµ РѕСЃС‚Р°СЋС‚СЃСЏ С‚РѕР»СЊРєРѕ РїРѕСЃС‚РѕСЏРЅРЅС‹Рµ Obsidian-РґР°РЅРЅС‹Рµ Рё Docker socket.

Р”Р»СЏ GitHub-Stack СѓРєР°Р¶РёС‚Рµ Compose path `gh_docker-compose.yml`, reference `refs/heads/main` Рё РїРµСЂРµРјРµРЅРЅС‹Рµ РёР· `.env.example`. Р”Р»СЏ РїСѓР±Р»РёС‡РЅРѕРіРѕ GHCR-РѕР±СЂР°Р·Р° authentication РЅРµ РЅСѓР¶РЅР°; РґР»СЏ РїСЂРёРІР°С‚РЅРѕРіРѕ РЅР°СЃС‚СЂРѕР№С‚Рµ registry credentials РІ Portainer.

## GitOps: merge РІ main в†’ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРѕРµ РѕР±РЅРѕРІР»РµРЅРёРµ

1. РЎРѕР·РґР°Р№С‚Рµ РІРµС‚РєСѓ `agent/<Р·Р°РґР°С‡Р°>`, РІРЅРµСЃРёС‚Рµ РёР·РјРµРЅРµРЅРёСЏ Рё РѕС‚РєСЂРѕР№С‚Рµ draft PR.
2. Workflow Р·Р°РїСѓСЃРєР°РµС‚ С‚РµСЃС‚С‹ РґР»СЏ PR, РЅРѕ РЅРµ РїСѓР±Р»РёРєСѓРµС‚ Рё РЅРµ СЂР°Р·РІРѕСЂР°С‡РёРІР°РµС‚ РІРµС‚РєСѓ.
3. РџРѕСЃР»Рµ merge РІ `main` workflow РїРѕРІС‚РѕСЂСЏРµС‚ РїСЂРѕРІРµСЂРєРё, РїСѓР±Р»РёРєСѓРµС‚ С‚РµРіРё `main` Рё `sha-<commit>` РІ GHCR.
4. Workflow РІС‹Р·С‹РІР°РµС‚ Portainer webhook С‚РѕР»СЊРєРѕ РµСЃР»Рё РІ GitHub Secrets Р·Р°РґР°РЅ `PORTAINER_WEBHOOK_URL`.
5. Portainer РїРѕРґС‚СЏРіРёРІР°РµС‚ РЅРѕРІС‹Р№ РѕР±СЂР°Р· Рё РїРµСЂРµР·Р°РїСѓСЃРєР°РµС‚ РµРґРёРЅСЃС‚РІРµРЅРЅС‹Р№ bot-РєРѕРЅС‚РµР№РЅРµСЂ.

Р’ Portainer РґР»СЏ GitHub Stack РІРєР»СЋС‡РёС‚Рµ GitOps updates в†’ **Webhook**, Р·Р°С‚РµРј **Re-pull image** Рё **Force redeployment**. Р”РѕР±Р°РІСЊС‚Рµ РІС‹РґР°РЅРЅС‹Р№ webhook URL РІ GitHub Actions Secret `PORTAINER_WEBHOOK_URL`; РЅРµ РєРѕРјРјРёС‚СЊС‚Рµ РµРіРѕ РІ СЂРµРїРѕР·РёС‚РѕСЂРёР№.

Р”Р»СЏ РїРµСЂРІРѕРіРѕ РїРµСЂРµС…РѕРґР° СЃРЅР°С‡Р°Р»Р° РґРѕР¶РґРёС‚РµСЃСЊ СѓСЃРїРµС€РЅРѕР№ РїСѓР±Р»РёРєР°С†РёРё GHCR-РѕР±СЂР°Р·Р°, Р·Р°С‚РµРј РІСЂСѓС‡РЅСѓСЋ СЂР°Р·РІРµСЂРЅРёС‚Рµ GitHub Stack. РџРѕСЃР»Рµ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ СЂР°Р±РѕС‚С‹ РІРєР»СЋС‡Р°Р№С‚Рµ webhook. РџРµСЂРµРґ Р·Р°РјРµРЅРѕР№ РѕСЃС‚Р°РЅРѕРІРёС‚Рµ СЃС‚Р°СЂС‹Р№ Stack: РґРІР° СЌРєР·РµРјРїР»СЏСЂР° СЃ РѕРґРЅРёРј `BOT_TOKEN` РєРѕРЅС„Р»РёРєС‚СѓСЋС‚ РїСЂРё polling, Р° РѕРґРёРЅР°РєРѕРІС‹Р№ `CONTAINER_NAME` РєРѕРЅС„Р»РёРєС‚СѓРµС‚ РІ Docker.

РћС‚РєР°С‚: РІ Portainer РІСЂРµРјРµРЅРЅРѕ СѓСЃС‚Р°РЅРѕРІРёС‚Рµ `IMAGE_TAG=sha-<РїСЂРµРґС‹РґСѓС‰РёР№-commit>` Рё СЃРґРµР»Р°Р№С‚Рµ redeploy. SHA-С‚РµРіРё РѕСЃС‚Р°СЋС‚СЃСЏ РїСЂРёРІСЏР·Р°РЅРЅС‹РјРё Рє РєРѕРЅРєСЂРµС‚РЅС‹Рј РїСЂРѕРІРµСЂРµРЅРЅС‹Рј commit.

## РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ

РЎРєРѕРїРёСЂСѓР№С‚Рµ `.env.example` РІ РїСЂРёРІР°С‚РЅС‹Р№ `.env` РґР»СЏ Р»РѕРєР°Р»СЊРЅРѕРіРѕ Р·Р°РїСѓСЃРєР° РёР»Рё РїРµСЂРµРЅРµСЃРёС‚Рµ Р·РЅР°С‡РµРЅРёСЏ РІ Portainer Environment Variables. РќРёРєРѕРіРґР° РЅРµ РґРѕР±Р°РІР»СЏР№С‚Рµ `.env` РІ Git.

| РџРµСЂРµРјРµРЅРЅР°СЏ | РќР°Р·РЅР°С‡РµРЅРёРµ |
| --- | --- |
| `BOT_TOKEN`, `PAID_KEY`, `ADMIN_ID` | Р”РѕСЃС‚СѓРї Telegram, OpenRouter Рё Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР° |
| `APP_PATH` | РўРѕР»СЊРєРѕ РґР»СЏ `docker-compose.yml` СЃ СЃРµСЂРІРµСЂРЅС‹Рј РёСЃС…РѕРґРЅС‹Рј РєРѕРґРѕРј |
| `BOT_IMAGE`, `IMAGE_TAG` | РўРѕР»СЊРєРѕ РґР»СЏ `gh_docker-compose.yml` Рё GHCR |
| `SAVE_PATH`, `ATTACHMENTS_PATH` | РџРѕСЃС‚РѕСЏРЅРЅС‹Рµ РґР°РЅРЅС‹Рµ Obsidian |
| `HTTP_PROXY`, `HTTPS_PROXY` | РќРµРѕР±СЏР·Р°С‚РµР»СЊРЅС‹Р№ proxy |
| `CONTAINER_NAME`, `DOCKER_SOCKET_PATH` | РљРѕРЅС‚РµР№РЅРµСЂ Рё Docker socket |
| `APPLICATION_NETWORK`, `PROXY_NETWORK` | РЎСѓС‰РµСЃС‚РІСѓСЋС‰РёРµ РІРЅРµС€РЅРёРµ Docker networks |

## РџСЂРѕРІРµСЂРєР°

```bash
python -B -m unittest discover -v -s tests
docker compose --env-file .env.example -f docker-compose.yml config
docker compose --env-file .env.example -f gh_docker-compose.yml config
```

![РџСЂРµРІСЊСЋ Р·Р°РјРµС‚РєРё Obsidian](assets/readme-hero.png)

<details>
<summary>Previous README versions</summary>

РџСѓР±Р»РёС‡РЅС‹С… РїСЂРµРґС‹РґСѓС‰РёС… РІРµСЂСЃРёР№ РїРѕРєР° РЅРµС‚.

</details>

<p align="right">Created by oxotn1k</p>

## Ручное переключение шлюза

Администратор может нажать 🔄 Переключить шлюз. Бот проверяет Telegram и OpenRouter через кандидатный шлюз, затем переключает оба клиента. Укажите PRIMARY_PROXY_URL и RESERVE_PROXY_URL только в Portainer или локальном .env; адреса и учётные данные не публикуются.
