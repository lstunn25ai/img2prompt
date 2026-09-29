# img2prompt (Initialization, Gateway Failover and Auto-pulling) — Контекст

> Создан: 2026-09-29 03:54 +03:00  
> Цель: Pre-compaction preservation / handoff  
> Покрытие: Инициализация проекта, аудит целостности версий (GitHub vs NAS vs Wiki), ликвидация аварии запуска (CrashLoop), исправление сетевых шлюзов v2rayA/mihomo, реализация авто-failover и Docker Unix Socket restart, настройка GitOps auto-pulling через вебхук Portainer.  
> Статус: completed  

---

## 1. Executive Summary
В ходе данной сессии выполнен полный цикл инициализации и восстановления работоспособности Telegram-бота **img2prompt** (OCR Vision Bot):
1. **Инициализация контракта**: согласованы 5 регламентных вопросов, созданы канонические файлы `PROJECT.md`, `PROJECT_LOG.md` и первичный снапшот в `docs/context/`.
2. **Ликвидация аварии CrashLoop**: обнаружена и исправлена ошибка `ModuleNotFoundError: No module named 'httpx'`, из-за которой контейнер `vision_bot` падал при старте. Добавлена зависимость `httpx` в `requirements.txt` и регрессионный тест в `tests/test_source_contract.py` (PR #6).
3. **Авто-failover и исправление сети прокси**:
   - Обнаружено несоответствие порта `bot_vpn_core:20171` (v2rayA слушает порт 20170). В `proxy_routing.py` внедрена авто-нормализация портов (`20171` -> `20170`) и опечаток (`mimoho` -> `mihomo`) (PR #7).
   - В `bot.py` добавлена функция `ensure_active_proxy_or_failover()`, устраняющая «ловушку мертвого шлюза»: бот при старте сам проверяет доступность шлюзов и бесшовно активирует рабочий резерв.
4. **Рестарт через Unix Socket**: в `bot.py` вызов `os.system("docker restart ...")` заменен на асинхронный вызов Docker Engine API к `/var/run/docker.sock` через `aiohttp.UnixConnector`, что ликвидировало ошибку `sh: 1: docker: not found`.
5. **GitOps Auto-pulling**: в GitHub Secrets обновлен `PORTAINER_WEBHOOK_URL` на боевой адрес `https://portainer.bro525.ru/api/stacks/webhooks/d82f564a-1b3e-4c76-a9dc-d486e28f3898`. Теперь при merge в `main` образ собирается в GHCR и автоматически за 3 секунды перекачивается в Portainer (`pull_policy: always`).
6. **Верификация в проде**: контейнер `vision_bot` переведен в статус `Up (healthy)`, подтвержден доступ к OpenRouter API (`200 OK`), бот `@img2prompt_25_bot` успешно запущен и ведет polling.

---

## 2. Архитектурная карта и реквизиты

| Параметр | Значение |
|---|---|
| **Репозиторий** | `https://github.com/lstunn25ai/img2prompt` (ветка `main`, последний коммит PR #7) |
| **Канонический путь NAS** | `V:\img2prompt` (`\\101.119.8.145\containers\img2prompt`) |
| **Стек в Portainer** | Стек 104 (`github_img2bot`), Endpoint 2 (`local`), образ `ghcr.io/lstunn25ai/img2prompt:main` |
| **Сетевые контуры** | `vpn_shared` (шлюз `mihomo:7890`), `botanswer_v12_stable_default` (шлюз `bot_vpn_core:20170`) |
| **Каноническая Wiki** | `W:\Documents\obsidian\AI\claude\wiki\projects\img2prompt.md` |
| **Журнал памяти** | `C:\Users\lstun\.agents\skills\memory\projects.md` (строка 15) |
| **Personal Agent Hub** | `https://hub.bro525.ru` (Стек 114 на NAS) |

---

## 3. Хронология решений и PR

1. **PR #5 (`docs: project initialization and Personal Agent Hub context`)**:
   - Добавлены `PROJECT.md`, `PROJECT_LOG.md`, первичный контекст в `docs/context/`.
2. **PR #6 (`fix: add httpx dependency, proxy auto-failover, and docker socket restart`)**:
   - `requirements.txt`: добавлен `httpx`.
   - `bot.py`: внедрен `ensure_active_proxy_or_failover()` и `restart_docker_container()`.
   - `tests/test_source_contract.py`: добавлен тест зависимостей.
3. **PR #7 (`fix: normalize bot_vpn_core port to 20170`)**:
   - `proxy_routing.py`: авто-нормализация `bot_vpn_core:20171` -> `20170` и `mimoho` -> `mihomo`.
   - `tests/test_proxy_routing.py`: тесты нормализации.
4. **Конфигурация GitHub Secrets**:
   - `PORTAINER_WEBHOOK_URL` переведен на домен `https://portainer.bro525.ru/api/stacks/webhooks/d82f564a-1b3e-4c76-a9dc-d486e28f3898`.

---

## 4. Evidence and Sources

| Item | Type | Pointer | Status | What it proves |
|---|---|---|---|---|
| Контейнер `vision_bot` | Docker Container | Portainer Stack 104 | confirmed | Статус `Up`, логи: `Run polling for bot @img2prompt_25_bot` |
| OpenRouter API | API Diagnostic | `https://openrouter.ai/api/v1/models` | confirmed | Код 200 OK через шлюз `http://mihomo:7890` |
| Вебхук Portainer | HTTP Webhook | `https://portainer.bro525.ru/...` | confirmed | HTTP 204 No Content, авто-пуллинг за 3 секунды |
| Тесты репозитория | Unit Tests | `tests/test_*.py` | confirmed | 100% PASS во всех PR (14-17s) |
| Каноническая Wiki | Obsidian Wiki | `W:\Documents\obsidian\AI\claude\wiki\projects\img2prompt.md` | confirmed | Актуализирована с отметкой 2026-09-29 |

---

## 5. Текущее состояние и следующий шаг
- **Бот полностью работоспособен в проде на NAS.**
- **Следующий шаг развития**: оптимизация логики формирования Obsidian-шаблона и OCR-распознавания альбомов при необходимости.
