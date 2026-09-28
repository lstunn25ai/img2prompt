# img2prompt (Project Initialization & Hub Integration) — Контекст

> Создан: 2026-09-29 01:56 +03:00  
> Цель: Handoff & Session State Preservation  
> Покрытие: Инициализация проекта в Antigravity, сравнение версий (GitHub vs NAS vs Wiki), аудит Personal Agent Hub (hub.bro525.ru), интеграция артефактов Graphify и AGENTS.md.  
> Статус: completed  

---

## 1. Executive Summary
Проведена первичная инициализация и сквозной аудит проекта **img2prompt** (OCR Vision Bot для Telegram) в связке с экосистемой **Personal Agent Hub (Forgejo)** на домашнем сервере NAS:
1. Подтверждена актуальность и целостность рабочей версии: код ветки GitHub `main` (`36b771e`) полностью соответствует коду на боевом сервере `V:\img2prompt` и локальному воркспейсу.
2. Проверена работоспособность портала **Personal Agent Hub** (`https://hub.bro525.ru`): Blazor Server, Zero Trust авторизация и WSS-туннель рабочей станции активны и стабильны.
3. В проект заведены регламентные файлы `PROJECT.md` и `PROJECT_LOG.md`, подтянуты серверные артефакты `AGENTS.md` и граф зависимостей `graphify-out/`.
4. Подготовлена база для трехуровневой синхронизации хэндоффов между Codex CLI, Antigravity и веб-интерфейсом Хаба.

---

## 2. Архитектурная карточка проекта

| Параметр | Значение |
|---|---|
| **Репозиторий** | `https://github.com/lstunn25ai/img2prompt` (ветка `main`) |
| **Серверный путь** | `V:\img2prompt` (`\\101.119.8.145\containers\img2prompt`) |
| **Портал управления** | `https://hub.bro525.ru` (Portainer Stack 114) |
| **Стек технологий** | Python 3.11, aiogram, OpenRouter API (Gemini Flash / GPT-4o-mini), Pillow, Docker Compose |
| **Выходные данные** | Markdown-заметки Obsidian Vault + оптимизированные JPEG-превью (до 300px, EXIF-corrected) |
| **Сеть и прокси** | Docker-сеть `vpn_shared`, primary HTTP-прокси `http://mihomo:7890`, резервный `vpn_mimoho` |
