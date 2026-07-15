import os
import asyncio
import json
import logging
import base64
import sys
import httpx
import re
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.session.aiohttp import AiohttpSession

from dotenv import load_dotenv
from openai import AsyncOpenAI

from proxy_routing import build_proxy_endpoints, load_proxy_index, next_proxy_index, save_proxy_index

from preview_assets import (
    create_preview_asset,
    render_attachment_markdown,
    save_preview_asset,
)

# =========================================================================================
# 1. СИСТЕМНЫЕ ПРАВА И НАСТРОЙКИ (КРИТИЧЕСКИЙ ФИКС EPERM)
# =========================================================================================

# Устанавливаем маску прав 0, чтобы все создаваемые ботом файлы
# получали максимальные разрешения (полезно для фикса EPERM на сетевых дисках).
os.umask(0)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# =========================================================================================
# 2. КОНФИГУРАЦИЯ И ЗАГРУЗКА ПАРАМЕТРОВ
# =========================================================================================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")
PAID_API_KEY = os.getenv("PAID_KEY", "").strip().strip('"').strip("'")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip())
INTERNAL_SAVE_PATH = os.getenv("SAVE_PATH", "").strip()
ATTACHMENTS_PATH = os.getenv("ATTACHMENTS_PATH", "").strip()
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "vision_bot").strip()

required_settings = {
    "BOT_TOKEN": BOT_TOKEN,
    "PAID_KEY": PAID_API_KEY,
    "ADMIN_ID": str(ADMIN_ID) if ADMIN_ID else "",
    "SAVE_PATH": INTERNAL_SAVE_PATH,
    "ATTACHMENTS_PATH": ATTACHMENTS_PATH,
}
missing_settings = [name for name, value in required_settings.items() if not value]
if missing_settings:
    logging.critical(
        "❌ ОШИБКА: В настройках Portainer (.env) отсутствуют: %s",
        ", ".join(missing_settings),
    )
    sys.exit(1)

PAID_BASE_URL = 'https://openrouter.ai/api/v1'
PRIMARY_PROXY_URL = os.getenv('PRIMARY_PROXY_URL', '').strip() or os.getenv('HTTP_PROXY', '').strip()
RESERVE_PROXY_URL = os.getenv('RESERVE_PROXY_URL', '').strip()
PROXY_ENDPOINTS = build_proxy_endpoints(PRIMARY_PROXY_URL, RESERVE_PROXY_URL)
PROXY_STATE_PATH = Path(INTERNAL_SAVE_PATH) / '.vision_bot_proxy_state'
CURRENT_PROXY_INDEX = load_proxy_index(PROXY_STATE_PATH, len(PROXY_ENDPOINTS))
PROXY_URL = PROXY_ENDPOINTS[CURRENT_PROXY_INDEX].url if PROXY_ENDPOINTS else None
MODELS_PRIORITY = ['google/gemini-2.5-flash', 'openai/gpt-4o-mini']

def create_openai_client(proxy_url):
    http_client = httpx.AsyncClient(proxy=proxy_url) if proxy_url else None
    return http_client, AsyncOpenAI(
        api_key=PAID_API_KEY,
        base_url=PAID_BASE_URL,
        http_client=http_client,
        default_headers={
            'HTTP-Referer': 'https://t.me/vision_bot',
            'X-Title': 'OCR_Vision_Bot',
        },
    )

session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else None
bot = Bot(token=BOT_TOKEN, session=session) if session else Bot(token=BOT_TOKEN)
dp = Dispatcher()
custom_http_client, client = create_openai_client(PROXY_URL)

USER_BATCHES = {}
BATCH_LOCK = asyncio.Lock()
LAST_RESTART_TIME = 0

# =========================================================================================
# 3. ЛОГИКА ШАБЛОНА OBSIDIAN
# =========================================================================================

def render_combined_note(results: list) -> str:
    if not results:
        return ""

    main_res = results[0]
    emoji = main_res.get('emoji')
    emoji = emoji if emoji else "📝"

    title = main_res.get('title')
    title = title if title else "Untitled"

    category = main_res.get('category')
    category = urllib.parse.unquote(str(category)) if category else "Inbox"

    base_links = ["[[prompt]]", "[[AI]]", "[[img2prompt]]"]
    all_raw_links = []

    for res in results:
        links = res.get('wiki_links') or []
        all_raw_links.extend(links)

    cleaned_links = []
    for link in all_raw_links:
        if "http" in str(link):
            name = str(link).rstrip('/').split('/')[-1].replace('_', ' ')
        else:
            name = str(link)

        name = urllib.parse.unquote(name)
        wiki_fmt = f"[[{name}]]"
        if wiki_fmt not in base_links and wiki_fmt not in cleaned_links:
            cleaned_links.append(wiki_fmt)

    links_str = " | ".join(base_links + cleaned_links[:4])

    base_tags = ["#Prompt", "#prompts", "#AI_Prompt", "#AI", "#img2prompt"]
    all_raw_tags = []

    for res in results:
        tags = res.get('tags') or []
        all_raw_tags.extend(tags)

    new_tags = []
    for tag in all_raw_tags:
        tag_decoded = urllib.parse.unquote(str(tag))
        fmt_tag = f"#{tag_decoded.replace(' ', '_')}"

        if fmt_tag.lower() not in [bt.lower() for bt in base_tags] and fmt_tag not in new_tags:
            new_tags.append(fmt_tag)

    tags_str = " ".join(base_tags + new_tags[:3])

    now = datetime.now().strftime("%d-%m-%Y")

    # ФИКС КОПИРОВАНИЯ: Генерируем тройные кавычки безопасно, чтобы Markdown не ломался
    ticks = "`" * 3

    sections = []
    for i, res in enumerate(results, 1):
        prompt = res.get('clean_prompt') or "[Текст не извлечен]"

        section_title = res.get('title')
        if not section_title or str(section_title).lower() == "untitled" or str(section_title).lower() == "none":
            section_title = f"Image {i}"
        else:
            section_title = urllib.parse.unquote(str(section_title))

        section_parts = [f"### {section_title}"]
        attachment_markdown = res.get('_attachment_markdown')
        if attachment_markdown:
            section_parts.append(attachment_markdown)
        section_parts.append(f"{ticks}text\n{prompt}\n{ticks}")
        sections.append("\n\n".join(section_parts))

    body_content = "\n\n".join(sections)
    header_text = f"AI ⚛️ {emoji} {title}"

    template = f"""{header_text}

> [!abstract] {links_str}

%%
Input links: [[{category}]] %%
Tags: {tags_str}
Date: {now} %% %%
Output links:

!!!

{body_content}"""

    return template

# =========================================================================================
# 4. ФАЙЛОВАЯ СИСТЕМА И СОХРАНЕНИЕ
# =========================================================================================

def sync_save_file(full_title_icons: str, content: str) -> str:
    safe_name = re.sub(r'[/*?:"<>|]', "", full_title_icons).strip() or "Untitled"
    file_path = os.path.join(INTERNAL_SAVE_PATH, f"{safe_name}.md")

    os.makedirs(INTERNAL_SAVE_PATH, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        os.chmod(file_path, 0o666)
    except Exception as e:
        logging.warning(f"Не удалось выставить chmod для {file_path}: {e}")

    logging.info(f"УСПЕХ: Файл записан: {file_path}")
    return file_path

async def save_markdown_file(title_icons: str, content: str) -> str:
    return await asyncio.wait_for(asyncio.to_thread(sync_save_file, title_icons, content), timeout=5.0)

# =========================================================================================
# 5. ДИАГНОСТИКА И UI
# =========================================================================================

async def check_diagnostics() -> str:
    report = []
    try:
        async with httpx.AsyncClient(proxy=PROXY_URL, timeout=10.0, follow_redirects=True) as hc:
            headers = {"Authorization": f"Bearer {PAID_API_KEY}"}
            r = await hc.get(f"{PAID_BASE_URL}/models", headers=headers)
            if r.status_code == 200:
                report.append("✅ HTTP Service: Подключен")
            else:
                report.append(f"❌ HTTP Service: Ошибка (Code {r.status_code})")
    except Exception:
        report.append("❌ HTTP Service: Ошибка сети/прокси")

    try:
        await asyncio.wait_for(client.models.list(), timeout=10.0)
        report.append("✅ AI Agent: OpenRouter API доступен")
    except Exception as e:
        report.append(f"❌ AI Agent: Ошибка API ({e})")

    try:
        os.makedirs(INTERNAL_SAVE_PATH, exist_ok=True)
        report.append("✅ Filesystem: Доступ к папке заметок подтвержден")
    except Exception:
        report.append("❌ Filesystem: Ошибка доступа к папке заметок")

    try:
        os.makedirs(ATTACHMENTS_PATH, exist_ok=True)
        if not os.access(ATTACHMENTS_PATH, os.W_OK):
            raise PermissionError("Папка attachments недоступна для записи")
        report.append("✅ Attachments: Доступ к папке изображений подтвержден")
    except Exception:
        report.append("❌ Attachments: Ошибка доступа к папке изображений")

    return "\n".join(report)

def get_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚀 Рестарт контейнера"), KeyboardButton(text="🔄 Переключить шлюз")]],
        resize_keyboard=True,
        is_persistent=True
    )


async def validate_proxy(proxy_url):
    test_session = AiohttpSession(proxy=proxy_url)
    test_bot = Bot(token=BOT_TOKEN, session=test_session)
    try:
        await asyncio.wait_for(test_bot.get_me(), timeout=10.0)
    finally:
        await test_session.close()

    async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0) as http_client:
        response = await http_client.get(
            f'{PAID_BASE_URL}/models',
            headers={'Authorization': f'Bearer {PAID_API_KEY}'},
        )
        response.raise_for_status()


async def activate_proxy(proxy_index):
    global CURRENT_PROXY_INDEX, PROXY_URL, custom_http_client, client
    endpoint = PROXY_ENDPOINTS[proxy_index]
    new_http_client, new_client = create_openai_client(endpoint.url)
    bot.session.proxy = endpoint.url
    PROXY_URL, CURRENT_PROXY_INDEX = endpoint.url, proxy_index
    custom_http_client, client = new_http_client, new_client
    save_proxy_index(PROXY_STATE_PATH, proxy_index)
    return endpoint.label


# =========================================================================================
# 6. ЯДРО OCR ОБРАБОТКИ
# =========================================================================================

def get_mime_type(data: bytes) -> str:
    if data.startswith(b'\xff\xd8\xff'): return 'image/jpeg'
    elif data.startswith(b'\x89PNG\r\n\x1a\n'): return 'image/png'
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP': return 'image/webp'
    return 'image/jpeg'

async def perform_ocr(file_obj, message_id, preferred_model=None) -> tuple[dict, bytes] | None:
    temp_path = f"temp_{message_id}.png"
    last_error = None
    try:
        await bot.download(file_obj, destination=temp_path)
        with open(temp_path, "rb") as f:
            image_bytes = f.read()

        b64_img = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = get_mime_type(image_bytes)

        REJECT = ["пришлите", "нужен скриншот", "загрузите изображение", "я не вижу"]
        models_to_try = [preferred_model] if preferred_model else MODELS_PRIORITY

        # ФИКС КОПИРОВАНИЯ: Маркер для парсинга JSON без прямых тройных кавычек
        marker = "`" * 3

        for model in models_to_try:
            for attempt in range(2):
                try:
                    logging.info(f"Запрос к {model} (MsgID: {message_id}, Попытка {attempt+1})...")
                    res = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": "Ты — строгий OCR-инструмент. Задача — извлечь текст из центральной части изображения.\nПравила:\n1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО переводить текст.\n2. Игнорируй визуальный мусор: водяные знаки, никнеймы (например, @teyllan), имена авторов.\n3. СКОПИРУЙ ВЕСЬ ТЕКСТ СЛОВО В СЛОВО, включая крупные заголовки и их номера (например '05. ПРОМПТ...').\n4. В поле `title` запиши главный заголовок с картинки (вместе с цифрами).\n5. В поле `clean_prompt` запиши основной текст-инструкцию.\n6. В поле `category` запиши одно главное смысловое слово (не имя автора!).\n7. Поля `wiki_links` и `tags`: проанализируй СМЫСЛ текста и сгенерируй теги/ссылки по теме. МАКСИМУМ 3 тега. Никаких авторов! Не используй URL-кодировку!\nВерни строго JSON: title, emoji, category, wiki_links, tags, clean_prompt."
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Выполни OCR. НЕ ПЕРЕВОДИ. ИЗВЛЕКИ ЗАГОЛОВКИ И ТЕКСТ БЕЗ АВТОРОВ. Верни JSON без URL-кодировки."},
                                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}", "detail": "high"}}
                                ]
                            }
                        ],
                        response_format={"type": "json_object"}
                    )

                    if not res or not res.choices:
                        break

                    raw_json = res.choices[0].message.content

                    # Безопасный парсинг без использования литерала тройных кавычек
                    if f"{marker}json" in raw_json:
                        raw_json = raw_json.split(f"{marker}json")[1].split(marker)[0].strip()

                    data = json.loads(raw_json)
                    data['_used_model'] = model

                    prompt_text = (data.get('clean_prompt') or "").lower()

                    if any(word in prompt_text for word in REJECT) or len(prompt_text) < 15:
                        logging.warning(f"Модель {model} выдала отказ.")
                        break

                    return data, image_bytes

                except Exception as e:
                    last_error = e
                    logging.warning(f"Сбой модели {model} (Попытка {attempt+1}): {e}")
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        await asyncio.sleep(4.0)
                        continue
                    break

        # Если ни одна модель не сработала, вызываем ошибку, чтобы конвейер знал об этом
        if last_error:
            raise Exception(last_error)
        return None

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# =========================================================================================
# 7. ОТПРАВКА ДЛИННЫХ СООБЩЕНИЙ (БЕЗОПАСНАЯ РАЗБИВКА)
# =========================================================================================

async def send_long_message(message: Message, md_content: str, path: str):
    """Разбивает длинный Markdown текст на части, чтобы не нарушать лимит Telegram (4096)."""
    MAX_LEN = 3900

    # ФИКС КОПИРОВАНИЯ: Никаких прямых тройных кавычек в f-строках
    ticks = "`" * 3

    if len(md_content) <= MAX_LEN:
        text_to_send = f"{ticks}markdown\n{md_content}\n{ticks}\n\n💾 **Сохранено в:**\n`{path}`"
        await message.answer(text_to_send)
        return

    chunks = [md_content[i:i+MAX_LEN] for i in range(0, len(md_content), MAX_LEN)]

    for i, chunk in enumerate(chunks):
        if i == len(chunks) - 1:
            text_to_send = f"{ticks}markdown\n{chunk}\n{ticks}\n\n💾 **Сохранено в:**\n`{path}`"
            await message.answer(text_to_send)
        else:
            text_to_send = f"{ticks}markdown\n{chunk}\n{ticks}"
            await message.answer(text_to_send)

# =========================================================================================
# 8. УМНЫЙ КОНВЕЙЕР (СБОР БЕЗЛИМИТНЫХ АЛЬБОМОВ И ОТЧЕТ ОБ ОШИБКАХ)
# =========================================================================================

async def process_batch_after_delay(user_id: int, delay: float):
    """Ждет `delay` секунд. Если новых картинок нет, обрабатывает всю накопившуюся стопку."""
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        # Таймер сброшен новой картинкой
        return

    async with BATCH_LOCK:
        batch_data = USER_BATCHES.pop(user_id, None)

    if not batch_data or not batch_data['messages']:
        return

    messages = batch_data['messages']
    # Сортируем по ID для правильного порядка
    messages.sort(key=lambda x: x.message_id)
    total = len(messages)
    first_msg = messages[0]

    try:
        status_msg = await first_msg.answer(f"⚛ Собрано {total} фото. Начинаю обработку...")

        results = []
        preview_warnings = []
        pinned_model = None

        for i, msg in enumerate(messages, 1):
            try:
                await status_msg.edit_text(f"⚛ **Статус:**\n🔍 Обработка {i} из {total}...")
            except:
                pass

            file_obj = msg.photo[-1] if msg.photo else msg.document

            try:
                ocr_result = await perform_ocr(file_obj, msg.message_id, preferred_model=pinned_model)
                if ocr_result:
                    res, image_bytes = ocr_result

                    if msg.document and msg.document.file_name:
                        display_name = msg.document.file_name
                    else:
                        display_name = f"Pasted image {datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"

                    try:
                        preview_asset = await asyncio.to_thread(
                            create_preview_asset,
                            image_bytes,
                            display_name,
                        )
                        preview_path, preview_created = await asyncio.to_thread(
                            save_preview_asset,
                            preview_asset,
                            ATTACHMENTS_PATH,
                        )
                        res['_attachment_markdown'] = render_attachment_markdown(preview_asset)
                        action = "создано" if preview_created else "переиспользовано"
                        logging.info(f"Превью {action}: {preview_path}")
                    except Exception as preview_err:
                        logging.error(f"Не удалось сохранить превью изображения {i}: {preview_err}")
                        preview_warnings.append(i)

                    results.append(res)
                    if not pinned_model and '_used_model' in res:
                        pinned_model = res['_used_model']
                else:
                    await first_msg.answer(f"⚠️ Изображение {i} пропущено: ИИ не нашел текст.")
            except Exception as item_err:
                logging.error(f"Ошибка картинки {i}: {item_err}")
                error_text = f"⚠️ Изображение {i} пропущено из-за ошибки сервера:\n`{item_err}`"
                await first_msg.answer(error_text)

            await asyncio.sleep(3.0)

        if results:
            md_content = render_combined_note(results)

            first_emoji = results[0].get('emoji') or ("📚" if total > 1 else "📝")
            first_title = results[0].get('title')
            first_title = urllib.parse.unquote(str(first_title)) if first_title and str(first_title).lower() != "none" else ("Batch" if total > 1 else "Untitled")

            header_icons = f"AI ⚛️ {first_emoji} {first_title}"
            path = await save_markdown_file(header_icons, md_content)

            if preview_warnings:
                indexes = ", ".join(str(index) for index in preview_warnings)
                await first_msg.answer(
                    f"⚠️ Не удалось сохранить превью для изображений: {indexes}. "
                    "Текст заметки сохранен без битых ссылок."
                )

            try: await status_msg.delete()
            except: pass

            await send_long_message(first_msg, md_content, path)
        else:
            await status_msg.edit_text("❌ Ошибка: Не удалось извлечь текст ни из одного изображения.")

    except Exception as global_err:
        logging.error(f"Критическая ошибка батча: {global_err}")
        try:
            error_text = f"❌ Критическая ошибка системы: `{global_err}`"
            await first_msg.answer(error_text)
        except: pass

@dp.message(F.photo | F.document)
async def handle_vision_request(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    user_id = message.from_user.id

    async with BATCH_LOCK:
        if user_id not in USER_BATCHES:
            USER_BATCHES[user_id] = {'messages': [], 'timer_task': None}

        USER_BATCHES[user_id]['messages'].append(message)

        # Если таймер уже тикает — сбрасываем его
        if USER_BATCHES[user_id]['timer_task']:
            USER_BATCHES[user_id]['timer_task'].cancel()

        # Запускаем новый таймер. 4.5 секунды тишины = конец загрузки альбома
        USER_BATCHES[user_id]['timer_task'] = asyncio.create_task(
            process_batch_after_delay(user_id, delay=4.5)
        )

# =========================================================================================
# 9. ТОЧКА ВХОДА
# =========================================================================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👋 oxotn1k готов к работе. Жду твои промпты и альбомы (любого размера).", reply_markup=get_kb())

@dp.message(F.text == "🚀 Рестарт контейнера")
async def restart_handler(message: Message):
    global LAST_RESTART_TIME
    if message.from_user.id != ADMIN_ID or time.time() - LAST_RESTART_TIME < 10:
        return

    LAST_RESTART_TIME = time.time()
    await message.answer("⏳ Перезагрузка Docker-контейнера...")
    os.system(f"docker restart {CONTAINER_NAME} &")

@dp.message(F.text == "🔄 Переключить шлюз")
async def manual_proxy_switch(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    if len(PROXY_ENDPOINTS) < 2:
        await message.answer('⚠️ Резервный шлюз не задан в настройках Portainer.')
        return

    next_index = next_proxy_index(CURRENT_PROXY_INDEX, len(PROXY_ENDPOINTS))
    candidate = PROXY_ENDPOINTS[next_index]
    status = await message.answer('🔄 Проверяю следующий шлюз перед переключением...')
    try:
        await validate_proxy(candidate.url)
        label = await activate_proxy(next_index)
        await status.edit_text(f'✅ Активирован {label.lower()} шлюз.')
    except Exception as error:
        logging.error('Проверка шлюза не прошла: %s', error)
        await status.edit_text('❌ Переключение отменено: следующий шлюз недоступен.')


async def main():
    logging.info("Инициализация системы (Старт диагностики)...")
    diag_report = await check_diagnostics()

    try:
        report_text = f"🚀 **Контейнер бота запущен!**\n\nСтартовая диагностика:\n\n{diag_report}"
        await bot.send_message(ADMIN_ID, report_text, reply_markup=get_kb())
    except Exception as e:
        logging.error(f"Не удалось отправить приветствие: {e}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Работа бота завершена штатно.")
