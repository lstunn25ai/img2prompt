# img2prompt — Журнал проекта (PROJECT_LOG)

**Канонический репозиторий:** `https://github.com/lstunn25ai/img2prompt`  
**Канонический путь на NAS:** `V:\img2prompt` (`\\101.119.8.145\containers\img2prompt`)  
**Wiki:** `wiki/projects/img2prompt.md`  
**Personal Agent Hub:** `https://hub.bro525.ru` (Стек 114 на NAS)  
**Дата сессии:** 2026-09-29  

---

## 1. Сводка сессии 1: Инициализация и аудит целостности

### 1.1. Что было (Исходное состояние)
1. Проект находился в рабочей ветке GitHub `main` (коммит `36b771e`), развёрнут в проде на NAS через Portainer Git Stack.
2. В локальном воркспейсе Antigravity отсутствовал корневой файл `PROJECT.md` и локальные хэндоффы сессий.
3. На сервере NAS присутствовал исторический `AGENTS.md` и артефакты `graphify-out/`, отсутствовавшие в гите.

### 1.2. Что сделано
1. Создан канонический `PROJECT.md` (Custom Instructions, связи Graphify, каноническая история).
2. Подтянуты артефакты `AGENTS.md` и `graphify-out/`.
3. Создан первичный снапшот сессии в `docs/context/`.
4. Слияние PR #5 в `main` (коммит `aa1cbb8`).

---

## 2. Сводка сессии 2: Ликвидация аварии запуска, авто-failover и сквозной GitOps

### 2.1. Что было (Причина аварии контейнера)
1. После обновления образа контейнер `vision_bot` перешёл в циклический CrashLoop (`Restarting (1)`):
   ```text
   ModuleNotFoundError: No module named 'httpx'
   ```
   В `requirements.txt` отсутствовала явная зависимость `httpx`, требуемая в `bot.py:7`.
2. Шаг авто-деплоя `notify-portainer` в GitHub Actions падал с ошибкой:
   ```text
   curl: (28) Failed to connect to 95.105.75.14 port 9000 after 10002 ms: Timeout was reached
   ```
   В GitHub Secrets `PORTAINER_WEBHOOK_URL` был указан устаревший внешний IP вместо домена `https://portainer.bro525.ru`.
3. Основной прокси `http://bot_vpn_core:20171` отдавал `Connection Refused` (v2rayA слушает порт 20170), а в резервном `mimoho` была опечатка.
4. Кнопка рестарта контейнера вызывала ошибку `sh: 1: docker: not found` из-за отсутствия CLI в slim-образе.

### 2.2. Что сделано (Решение)
1. **Зависимости:** В `requirements.txt` добавлен `httpx`, покрыт контрактным тестом в `tests/test_source_contract.py`.
2. **Автоматический Failover прокси:** В `bot.py` реализована функция `ensure_active_proxy_or_failover()`, проверяющая доступность шлюзов при старте.
3. **Авто-нормализация портов и опечаток:** В `proxy_routing.py` функция `normalize_proxy_url()` теперь автоматически исправляет опечатку `mimoho` -> `mihomo` и порт `bot_vpn_core:20171` -> `bot_vpn_core:20170`.
4. **Рестарт через Unix Socket:** В `bot.py` добавлен `restart_docker_container()` через `aiohttp.UnixConnector` к `/var/run/docker.sock` (Docker Engine API `/v1.41/containers/{name}/restart`) без использования утилиты `docker`.
5. **GitOps Auto-pulling:** В GitHub Secrets обновлён `PORTAINER_WEBHOOK_URL` на `https://portainer.bro525.ru/api/stacks/webhooks/d82f564a-1b3e-4c76-a9dc-d486e28f3898`.
6. Сформированы и успешно протестированы PR #6 и PR #7, слиты в `main`.

### 2.3. Результат
- GitHub Actions отработал: `test` (14s) -> `publish` (33s) -> `notify-portainer` (3s).
- Portainer принял webhook, автоматически перекачал образ `ghcr.io/lstunn25ai/img2prompt:main` и поднял контейнер.
- **Статус контейнера `vision_bot`**: `Up`, `running`.
- **Логи бота**:
  - `HTTP Request: GET https://openrouter.ai/api/v1/models "HTTP/1.1 200 OK"`
  - `Текущий шлюз Резервный (http://mihomo:7890) валиден.`
  - `Run polling for bot @img2prompt_25_bot id=8615328760 - 'img2prompt'`
- Бот полностью в строю, слушает Telegram и выполняет OCR.

---

## 3. База знаний по дебагу и Runbook при сбоях (Troubleshooting Guide)

Если бот перестаёт отвечать в Telegram или падает контейнер `vision_bot`, следовать этой пошаговой инструкции.

### 3.1. Быстрое сопоставление симптомов (Что сломалось → Как починили)

| Симптом / Ошибка в логах | Причина | Как починили / Что делать |
|---|---|---|
| `ModuleNotFoundError: No module named 'httpx'` (или любой другой модуль) | Пакет не был зафиксирован в `requirements.txt` | Добавить пакет в `requirements.txt`, запустить `pytest tests/test_source_contract.py`, создать PR и влить в `main`. Образ пересоберётся автоматически. |
| `sh: 1: docker: not found` | В `python:3.11-slim` нет бинарника `docker` CLI | Взаимодействие с Docker переведено на UNIX-сокет `/var/run/docker.sock` через Docker Engine API (`restart_docker_container()` в `bot.py`). Проверить наличие volume `/var/run/docker.sock:/var/run/docker.sock` в compose. |
| `ClientHttpProxyError: Cannot connect to host mimoho:7890` | Опечатка `mimoho` вместо `mihomo` в DNS имени | В `proxy_routing.py` внедрена авто-санитизация `normalize_proxy_url()`, которая заменяет `mimoho` на `mihomo`. В Portainer Stack Env исправить опечатку на каноничную. |
| `ClientHttpProxyError: Cannot connect to host bot_vpn_core:20171` | Неверный inbound порт v2rayA (порт 20171 закрыт/не слушает) | В `proxy_routing.py` внедрена авто-замена порта `20171` на `20170`. При необходимости проверить статус контейнера `bot_vpn_core` в сети `vpn_shared`. |
| Бот висит при старте / не подключается к OpenRouter | Основной шлюз недоступен из-за блокировки провайдера | Функция `ensure_active_proxy_or_failover()` автоматически переключается на рабочий резервный шлюз. Проверить логи: `Текущий шлюз ... валиден`. |
| Git push зависает в Windows PowerShell | Перехват трафика Git Credential Manager или локальным прокси `127.0.0.1:10809` | Использовать GitHub CLI: `gh pr create`, `gh pr merge`. Не вызывать интерактивный `git push` напрямую без флагов. |

### 3.2. Команды для оперативной диагностики

```powershell
# 1. Проверка статуса контейнера vision_bot через Portainer MCP:
portainer_list_containers(endpoint_id=2, filter_name="vision_bot")

# 2. Получение последних 50 строк логов с таймстемпами:
portainer_get_container_logs(endpoint_id=2, container_id_or_name="vision_bot", tail=50, timestamps=true)

# 3. Проверка доступности прокси-шлюзов с хоста NAS (через SSH):
curl -x http://127.0.0.1:7890 https://openrouter.ai/api/v1/models -I
curl -x http://127.0.0.1:20170 https://openrouter.ai/api/v1/models -I

# 4. Принудительный триггер вебхука авто-деплоя Portainer:
Invoke-RestMethod -Uri "https://portainer.bro525.ru/api/stacks/webhooks/d82f564a-1b3e-4c76-a9dc-d486e28f3898" -Method Post
```

### 3.3. Архитектура и поток работы (Как теперь работает)
1. **GitHub Actions (`ci.yml`):**
   `Push to main` → `pytest` → `ghcr.io/lstunn25ai/img2prompt:main` сборка и публикация → `POST Webhook to Portainer`.
2. **Portainer (Стек 104, `vision_bot`):**
   Приём вебхука → `docker pull ghcr.io/lstunn25ai/img2prompt:main` (`pull_policy: always`) → рестарт контейнера с сохранением томов.
3. **Инициализация `bot.py`:**
   `os.umask(0)` → проверка шлюзов `ensure_active_proxy_or_failover()` (тест `https://openrouter.ai/api/v1/models`) → запуск `aiogram.Dispatcher` polling.
4. **Хранение:**
   Все заметки сохраняются в `SAVE_PATH` (`V:\img2prompt\notes` / Obsidian Vault), превью сохраняются в `ATTACHMENTS_PATH` с правами `0o666` для предотвращения Permission Denied в Obsidian.

---

## 4. Сводка сессии 3: Сохранение изображений без текста и расширение fallback-моделей

### 4.1. Проблема
- При отправке альбомов, где часть картинок — иллюстрации/генерации без текста, бот пропускал их (`⚠️ Изображение X пропущено: ИИ не нашел текст`), не сохранял превью в `ATTACHMENTS_PATH` и не включал в заметку.
- Если все картинки батча были без текста, заметка не создавалась вовсе.
- Механизм `pinned_model` при отказе Gemini не переключался на резервную модель `openai/gpt-4o-mini`.
- Предыдущий тест пользователя оборвался на 3-й картинке из-за автоматического редеплоя по вебхуку (SIGTERM).

### 4.2. Решение
1. `perform_ocr` теперь возвращает `(None, image_bytes)` при отсутствии текста, что позволяет конвейеру обработать изображение.
2. В `models_to_try` сохранён полный список fallback-моделей: `[preferred_model] + [m for m in MODELS_PRIORITY if m != preferred_model]`.
3. В `process_batch_after_delay` для каждого изображения без текста превью гарантированно сохраняется в `ATTACHMENTS_PATH`, а в заметку добавляется секция с превью и меткой `[Изображение без текста]`.
4. В `render_combined_note` заголовок, эмодзи и теги заметки берутся из первого изображения с реальным OCR-текстом (если оно есть в батче), сохраняя чистую структуру Obsidian.
5. Контракт зафиксирован в `tests/test_source_contract.py`.


