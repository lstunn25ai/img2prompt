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

from preview_assets import (
    create_preview_asset,
    render_attachment_markdown,
    save_preview_asset,
)

# =========================================================================================
# 1. РЎРРЎРўР•РњРќР«Р• РџР РђР’Рђ Р РќРђРЎРўР РћР™РљР (РљР РРўРР§Р•РЎРљРР™ Р¤РРљРЎ EPERM)
# =========================================================================================

# РЈСЃС‚Р°РЅР°РІР»РёРІР°РµРј РјР°СЃРєСѓ РїСЂР°РІ 0, С‡С‚РѕР±С‹ РІСЃРµ СЃРѕР·РґР°РІР°РµРјС‹Рµ Р±РѕС‚РѕРј С„Р°Р№Р»С‹ 
# РїРѕР»СѓС‡Р°Р»Рё РјР°РєСЃРёРјР°Р»СЊРЅС‹Рµ СЂР°Р·СЂРµС€РµРЅРёСЏ (РїРѕР»РµР·РЅРѕ РґР»СЏ С„РёРєСЃР° EPERM РЅР° СЃРµС‚РµРІС‹С… РґРёСЃРєР°С…).
os.umask(0)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# =========================================================================================
# 2. РљРћРќР¤РР“РЈР РђР¦РРЇ Р Р—РђР“Р РЈР—РљРђ РџРђР РђРњР•РўР РћР’
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
        "вќЊ РћРЁРР‘РљРђ: Р’ РЅР°СЃС‚СЂРѕР№РєР°С… Portainer (.env) РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚: %s",
        ", ".join(missing_settings),
    )
    sys.exit(1)

PAID_BASE_URL = "https://openrouter.ai/api/v1"
PRIMARY_PROXY_URL = os.getenv("PRIMARY_PROXY_URL", "").strip() or os.getenv("HTTP_PROXY", "").strip()
RESERVE_PROXY_URL = os.getenv("RESERVE_PROXY_URL", "").strip()
PROXY_ENDPOINTS = build_proxy_endpoints(PRIMARY_PROXY_URL, RESERVE_PROXY_URL)
PROXY_STATE_PATH = Path(INTERNAL_SAVE_PATH) / ".vision_bot_proxy_state"
CURRENT_PROXY_INDEX = load_proxy_index(PROXY_STATE_PATH, len(PROXY_ENDPOINTS))
PROXY_URL = PROXY_ENDPOINTS[CURRENT_PROXY_INDEX].url if PROXY_ENDPOINTS else None
MODELS_PRIORITY = ["google/gemini-2.5-flash", "openai/gpt-4o-mini"]

def create_openai_client(proxy_url):
    http_client = httpx.AsyncClient(proxy=proxy_url) if proxy_url else None
    return http_client, AsyncOpenAI(api_key=PAID_API_KEY, base_url=PAID_BASE_URL, http_client=http_client, default_headers={"HTTP-Referer": "https://t.me/vision_bot", "X-Title": "OCR_Vision_Bot"})

session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else None
bot = Bot(token=BOT_TOKEN, session=session) if session else Bot(token=BOT_TOKEN)
dp = Dispatcher()
custom_http_client, client = create_openai_client(PROXY_URL)
# Р“Р»РѕР±Р°Р»СЊРЅС‹Рµ С…СЂР°РЅРёР»РёС‰Р° РґР°РЅРЅС‹С… РґР»СЏ РЈРњРќРћР“Рћ РўРђР™РњР•Р Рђ (РЎР±РѕСЂ Р±РµР·Р»РёРјРёС‚РЅС‹С… Р°Р»СЊР±РѕРјРѕРІ)
USER_BATCHES = {}
BATCH_LOCK = asyncio.Lock()
LAST_RESTART_TIME = 0

# =========================================================================================
# 3. Р›РћР“РРљРђ РЁРђР‘Р›РћРќРђ OBSIDIAN
# =========================================================================================

def render_combined_note(results: list) -> str:
    if not results:
        return ""
    
    main_res = results[0]
    emoji = main_res.get('emoji')
    emoji = emoji if emoji else "рџ“ќ"
    
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
    
    # Р¤РРљРЎ РљРћРџРР РћР’РђРќРРЇ: Р“РµРЅРµСЂРёСЂСѓРµРј С‚СЂРѕР№РЅС‹Рµ РєР°РІС‹С‡РєРё Р±РµР·РѕРїР°СЃРЅРѕ, С‡С‚РѕР±С‹ Markdown РЅРµ Р»РѕРјР°Р»СЃСЏ
    ticks = "`" * 3
    
    sections = []
    for i, res in enumerate(results, 1):
        prompt = res.get('clean_prompt') or "[РўРµРєСЃС‚ РЅРµ РёР·РІР»РµС‡РµРЅ]"
        
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
    header_text = f"AI вљ›пёЏ {emoji} {title}"
    
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
# 4. Р¤РђР™Р›РћР’РђРЇ РЎРРЎРўР•РњРђ Р РЎРћРҐР РђРќР•РќРР•
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
        logging.warning(f"РќРµ СѓРґР°Р»РѕСЃСЊ РІС‹СЃС‚Р°РІРёС‚СЊ chmod РґР»СЏ {file_path}: {e}")
        
    logging.info(f"РЈРЎРџР•РҐ: Р¤Р°Р№Р» Р·Р°РїРёСЃР°РЅ: {file_path}")
    return file_path

async def save_markdown_file(title_icons: str, content: str) -> str:
    return await asyncio.wait_for(asyncio.to_thread(sync_save_file, title_icons, content), timeout=5.0)

# =========================================================================================
# 5. Р”РРђР“РќРћРЎРўРРљРђ Р UI
# =========================================================================================

async def check_diagnostics() -> str:
    report = []
    try:
        async with httpx.AsyncClient(proxy=PROXY_URL, timeout=10.0, follow_redirects=True) as hc:
            headers = {"Authorization": f"Bearer {PAID_API_KEY}"}
            r = await hc.get(f"{PAID_BASE_URL}/models", headers=headers)
            if r.status_code == 200:
                report.append("вњ… HTTP Service: РџРѕРґРєР»СЋС‡РµРЅ")
            else:
                report.append(f"вќЊ HTTP Service: РћС€РёР±РєР° (Code {r.status_code})")
    except Exception:
        report.append("вќЊ HTTP Service: РћС€РёР±РєР° СЃРµС‚Рё/РїСЂРѕРєСЃРё")
        
    try:
        await asyncio.wait_for(client.models.list(), timeout=10.0)
        report.append("вњ… AI Agent: OpenRouter API РґРѕСЃС‚СѓРїРµРЅ")
    except Exception as e:
        report.append(f"вќЊ AI Agent: РћС€РёР±РєР° API ({e})")
        
    try:
        os.makedirs(INTERNAL_SAVE_PATH, exist_ok=True)
        report.append("вњ… Filesystem: Р”РѕСЃС‚СѓРї Рє РїР°РїРєРµ Р·Р°РјРµС‚РѕРє РїРѕРґС‚РІРµСЂР¶РґРµРЅ")
    except Exception:
        report.append("вќЊ Filesystem: РћС€РёР±РєР° РґРѕСЃС‚СѓРїР° Рє РїР°РїРєРµ Р·Р°РјРµС‚РѕРє")

    try:
        os.makedirs(ATTACHMENTS_PATH, exist_ok=True)
        if not os.access(ATTACHMENTS_PATH, os.W_OK):
            raise PermissionError("РџР°РїРєР° attachments РЅРµРґРѕСЃС‚СѓРїРЅР° РґР»СЏ Р·Р°РїРёСЃРё")
        report.append("вњ… Attachments: Р”РѕСЃС‚СѓРї Рє РїР°РїРєРµ РёР·РѕР±СЂР°Р¶РµРЅРёР№ РїРѕРґС‚РІРµСЂР¶РґРµРЅ")
    except Exception:
        report.append("вќЊ Attachments: РћС€РёР±РєР° РґРѕСЃС‚СѓРїР° Рє РїР°РїРєРµ РёР·РѕР±СЂР°Р¶РµРЅРёР№")
        
    return "\n".join(report)

def get_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="рџљЂ Р РµСЃС‚Р°СЂС‚ РєРѕРЅС‚РµР№РЅРµСЂР°"), KeyboardButton(text="рџ”„ РџРµСЂРµРєР»СЋС‡РёС‚СЊ С€Р»СЋР·")]], 
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
        response = await http_client.get(f"{PAID_BASE_URL}/models", headers={"Authorization": f"Bearer {PAID_API_KEY}"})
        response.raise_for_status()

async def activate_proxy(proxy_index):
    global CURRENT_PROXY_INDEX, PROXY_URL, custom_http_client, client
    endpoint = PROXY_ENDPOINTS[proxy_index]
    new_http_client, new_client = create_openai_client(endpoint.url)
    bot.session.proxy = endpoint.url
    custom_http_client, client = new_http_client, new_client
    PROXY_URL, CURRENT_PROXY_INDEX = endpoint.url, proxy_index
    save_proxy_index(PROXY_STATE_PATH, proxy_index)
    return endpoint.label# =========================================================================================
# 6. РЇР”Р Рћ OCR РћР‘Р РђР‘РћРўРљР
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
        
        REJECT = ["РїСЂРёС€Р»РёС‚Рµ", "РЅСѓР¶РµРЅ СЃРєСЂРёРЅС€РѕС‚", "Р·Р°РіСЂСѓР·РёС‚Рµ РёР·РѕР±СЂР°Р¶РµРЅРёРµ", "СЏ РЅРµ РІРёР¶Сѓ"]
        models_to_try = [preferred_model] if preferred_model else MODELS_PRIORITY
        
        # Р¤РРљРЎ РљРћРџРР РћР’РђРќРРЇ: РњР°СЂРєРµСЂ РґР»СЏ РїР°СЂСЃРёРЅРіР° JSON Р±РµР· РїСЂСЏРјС‹С… С‚СЂРѕР№РЅС‹С… РєР°РІС‹С‡РµРє
        marker = "`" * 3
        
        for model in models_to_try:
            for attempt in range(2):
                try:
                    logging.info(f"Р—Р°РїСЂРѕСЃ Рє {model} (MsgID: {message_id}, РџРѕРїС‹С‚РєР° {attempt+1})...")
                    res = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system", 
                                "content": "РўС‹ вЂ” СЃС‚СЂРѕРіРёР№ OCR-РёРЅСЃС‚СЂСѓРјРµРЅС‚. Р—Р°РґР°С‡Р° вЂ” РёР·РІР»РµС‡СЊ С‚РµРєСЃС‚ РёР· С†РµРЅС‚СЂР°Р»СЊРЅРѕР№ С‡Р°СЃС‚Рё РёР·РѕР±СЂР°Р¶РµРЅРёСЏ.\nРџСЂР°РІРёР»Р°:\n1. РљРђРўР•Р“РћР РР§Р•РЎРљР Р—РђРџР Р•Р©Р•РќРћ РїРµСЂРµРІРѕРґРёС‚СЊ С‚РµРєСЃС‚.\n2. РРіРЅРѕСЂРёСЂСѓР№ РІРёР·СѓР°Р»СЊРЅС‹Р№ РјСѓСЃРѕСЂ: РІРѕРґСЏРЅС‹Рµ Р·РЅР°РєРё, РЅРёРєРЅРµР№РјС‹ (РЅР°РїСЂРёРјРµСЂ, @teyllan), РёРјРµРЅР° Р°РІС‚РѕСЂРѕРІ.\n3. РЎРљРћРџРР РЈР™ Р’Р•РЎР¬ РўР•РљРЎРў РЎР›РћР’Рћ Р’ РЎР›РћР’Рћ, РІРєР»СЋС‡Р°СЏ РєСЂСѓРїРЅС‹Рµ Р·Р°РіРѕР»РѕРІРєРё Рё РёС… РЅРѕРјРµСЂР° (РЅР°РїСЂРёРјРµСЂ '05. РџР РћРњРџРў...').\n4. Р’ РїРѕР»Рµ `title` Р·Р°РїРёС€Рё РіР»Р°РІРЅС‹Р№ Р·Р°РіРѕР»РѕРІРѕРє СЃ РєР°СЂС‚РёРЅРєРё (РІРјРµСЃС‚Рµ СЃ С†РёС„СЂР°РјРё).\n5. Р’ РїРѕР»Рµ `clean_prompt` Р·Р°РїРёС€Рё РѕСЃРЅРѕРІРЅРѕР№ С‚РµРєСЃС‚-РёРЅСЃС‚СЂСѓРєС†РёСЋ.\n6. Р’ РїРѕР»Рµ `category` Р·Р°РїРёС€Рё РѕРґРЅРѕ РіР»Р°РІРЅРѕРµ СЃРјС‹СЃР»РѕРІРѕРµ СЃР»РѕРІРѕ (РЅРµ РёРјСЏ Р°РІС‚РѕСЂР°!).\n7. РџРѕР»СЏ `wiki_links` Рё `tags`: РїСЂРѕР°РЅР°Р»РёР·РёСЂСѓР№ РЎРњР«РЎР› С‚РµРєСЃС‚Р° Рё СЃРіРµРЅРµСЂРёСЂСѓР№ С‚РµРіРё/СЃСЃС‹Р»РєРё РїРѕ С‚РµРјРµ. РњРђРљРЎРРњРЈРњ 3 С‚РµРіР°. РќРёРєР°РєРёС… Р°РІС‚РѕСЂРѕРІ! РќРµ РёСЃРїРѕР»СЊР·СѓР№ URL-РєРѕРґРёСЂРѕРІРєСѓ!\nР’РµСЂРЅРё СЃС‚СЂРѕРіРѕ JSON: title, emoji, category, wiki_links, tags, clean_prompt."
                            },
                            {
                                "role": "user", 
                                "content": [
                                    {"type": "text", "text": "Р’С‹РїРѕР»РЅРё OCR. РќР• РџР•Р Р•Р’РћР”Р. РР—Р’Р›Р•РљР Р—РђР“РћР›РћР’РљР Р РўР•РљРЎРў Р‘Р•Р— РђР’РўРћР РћР’. Р’РµСЂРЅРё JSON Р±РµР· URL-РєРѕРґРёСЂРѕРІРєРё."},
                                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}", "detail": "high"}}
                                ]
                            }
                        ], 
                        response_format={"type": "json_object"}
                    )
                    
                    if not res or not res.choices:
                        break 
                        
                    raw_json = res.choices[0].message.content
                    
                    # Р‘РµР·РѕРїР°СЃРЅС‹Р№ РїР°СЂСЃРёРЅРі Р±РµР· РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ Р»РёС‚РµСЂР°Р»Р° С‚СЂРѕР№РЅС‹С… РєР°РІС‹С‡РµРє
                    if f"{marker}json" in raw_json:
                        raw_json = raw_json.split(f"{marker}json")[1].split(marker)[0].strip()
                    
                    data = json.loads(raw_json)
                    data['_used_model'] = model 
                    
                    prompt_text = (data.get('clean_prompt') or "").lower()
                    
                    if any(word in prompt_text for word in REJECT) or len(prompt_text) < 15:
                        logging.warning(f"РњРѕРґРµР»СЊ {model} РІС‹РґР°Р»Р° РѕС‚РєР°Р·.")
                        break
                    
                    return data, image_bytes
                    
                except Exception as e:
                    last_error = e
                    logging.warning(f"РЎР±РѕР№ РјРѕРґРµР»Рё {model} (РџРѕРїС‹С‚РєР° {attempt+1}): {e}")
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        await asyncio.sleep(4.0)
                        continue
                    break 
        
        # Р•СЃР»Рё РЅРё РѕРґРЅР° РјРѕРґРµР»СЊ РЅРµ СЃСЂР°Р±РѕС‚Р°Р»Р°, РІС‹Р·С‹РІР°РµРј РѕС€РёР±РєСѓ, С‡С‚РѕР±С‹ РєРѕРЅРІРµР№РµСЂ Р·РЅР°Р» РѕР± СЌС‚РѕРј
        if last_error:
            raise Exception(last_error)
        return None
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# =========================================================================================
# 7. РћРўРџР РђР’РљРђ Р”Р›РРќРќР«РҐ РЎРћРћР‘Р©Р•РќРР™ (Р‘Р•Р—РћРџРђРЎРќРђРЇ Р РђР—Р‘РР’РљРђ)
# =========================================================================================

async def send_long_message(message: Message, md_content: str, path: str):
    """Р Р°Р·Р±РёРІР°РµС‚ РґР»РёРЅРЅС‹Р№ Markdown С‚РµРєСЃС‚ РЅР° С‡Р°СЃС‚Рё, С‡С‚РѕР±С‹ РЅРµ РЅР°СЂСѓС€Р°С‚СЊ Р»РёРјРёС‚ Telegram (4096)."""
    MAX_LEN = 3900 
    
    # Р¤РРљРЎ РљРћРџРР РћР’РђРќРРЇ: РќРёРєР°РєРёС… РїСЂСЏРјС‹С… С‚СЂРѕР№РЅС‹С… РєР°РІС‹С‡РµРє РІ f-СЃС‚СЂРѕРєР°С…
    ticks = "`" * 3
    
    if len(md_content) <= MAX_LEN:
        text_to_send = f"{ticks}markdown\n{md_content}\n{ticks}\n\nрџ’ѕ **РЎРѕС…СЂР°РЅРµРЅРѕ РІ:**\n`{path}`"
        await message.answer(text_to_send)
        return
        
    chunks = [md_content[i:i+MAX_LEN] for i in range(0, len(md_content), MAX_LEN)]
    
    for i, chunk in enumerate(chunks):
        if i == len(chunks) - 1:
            text_to_send = f"{ticks}markdown\n{chunk}\n{ticks}\n\nрџ’ѕ **РЎРѕС…СЂР°РЅРµРЅРѕ РІ:**\n`{path}`"
            await message.answer(text_to_send)
        else:
            text_to_send = f"{ticks}markdown\n{chunk}\n{ticks}"
            await message.answer(text_to_send)

# =========================================================================================
# 8. РЈРњРќР«Р™ РљРћРќР’Р•Р™Р•Р  (РЎР‘РћР  Р‘Р•Р—Р›РРњРРўРќР«РҐ РђР›Р¬Р‘РћРњРћР’ Р РћРўР§Р•Рў РћР‘ РћРЁРР‘РљРђРҐ)
# =========================================================================================

async def process_batch_after_delay(user_id: int, delay: float):
    """Р–РґРµС‚ `delay` СЃРµРєСѓРЅРґ. Р•СЃР»Рё РЅРѕРІС‹С… РєР°СЂС‚РёРЅРѕРє РЅРµС‚, РѕР±СЂР°Р±Р°С‚С‹РІР°РµС‚ РІСЃСЋ РЅР°РєРѕРїРёРІС€СѓСЋСЃСЏ СЃС‚РѕРїРєСѓ."""
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        # РўР°Р№РјРµСЂ СЃР±СЂРѕС€РµРЅ РЅРѕРІРѕР№ РєР°СЂС‚РёРЅРєРѕР№
        return 

    async with BATCH_LOCK:
        batch_data = USER_BATCHES.pop(user_id, None)

    if not batch_data or not batch_data['messages']:
        return

    messages = batch_data['messages']
    # РЎРѕСЂС‚РёСЂСѓРµРј РїРѕ ID РґР»СЏ РїСЂР°РІРёР»СЊРЅРѕРіРѕ РїРѕСЂСЏРґРєР°
    messages.sort(key=lambda x: x.message_id)
    total = len(messages)
    first_msg = messages[0]

    try:
        status_msg = await first_msg.answer(f"вљ› РЎРѕР±СЂР°РЅРѕ {total} С„РѕС‚Рѕ. РќР°С‡РёРЅР°СЋ РѕР±СЂР°Р±РѕС‚РєСѓ...")
        
        results = []
        preview_warnings = []
        pinned_model = None 

        for i, msg in enumerate(messages, 1):
            try: 
                await status_msg.edit_text(f"вљ› **РЎС‚Р°С‚СѓСЃ:**\nрџ”Ќ РћР±СЂР°Р±РѕС‚РєР° {i} РёР· {total}...")
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
                        action = "СЃРѕР·РґР°РЅРѕ" if preview_created else "РїРµСЂРµРёСЃРїРѕР»СЊР·РѕРІР°РЅРѕ"
                        logging.info(f"РџСЂРµРІСЊСЋ {action}: {preview_path}")
                    except Exception as preview_err:
                        logging.error(f"РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕС…СЂР°РЅРёС‚СЊ РїСЂРµРІСЊСЋ РёР·РѕР±СЂР°Р¶РµРЅРёСЏ {i}: {preview_err}")
                        preview_warnings.append(i)

                    results.append(res)
                    if not pinned_model and '_used_model' in res:
                        pinned_model = res['_used_model']
                else:
                    await first_msg.answer(f"вљ пёЏ РР·РѕР±СЂР°Р¶РµРЅРёРµ {i} РїСЂРѕРїСѓС‰РµРЅРѕ: РР РЅРµ РЅР°С€РµР» С‚РµРєСЃС‚.")
            except Exception as item_err:
                logging.error(f"РћС€РёР±РєР° РєР°СЂС‚РёРЅРєРё {i}: {item_err}")
                error_text = f"вљ пёЏ РР·РѕР±СЂР°Р¶РµРЅРёРµ {i} РїСЂРѕРїСѓС‰РµРЅРѕ РёР·-Р·Р° РѕС€РёР±РєРё СЃРµСЂРІРµСЂР°:\n`{item_err}`"
                await first_msg.answer(error_text)
            
            await asyncio.sleep(3.0) 

        if results:
            md_content = render_combined_note(results)
            
            first_emoji = results[0].get('emoji') or ("рџ“љ" if total > 1 else "рџ“ќ")
            first_title = results[0].get('title')
            first_title = urllib.parse.unquote(str(first_title)) if first_title and str(first_title).lower() != "none" else ("Batch" if total > 1 else "Untitled")
            
            header_icons = f"AI вљ›пёЏ {first_emoji} {first_title}"
            path = await save_markdown_file(header_icons, md_content)

            if preview_warnings:
                indexes = ", ".join(str(index) for index in preview_warnings)
                await first_msg.answer(
                    f"вљ пёЏ РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕС…СЂР°РЅРёС‚СЊ РїСЂРµРІСЊСЋ РґР»СЏ РёР·РѕР±СЂР°Р¶РµРЅРёР№: {indexes}. "
                    "РўРµРєСЃС‚ Р·Р°РјРµС‚РєРё СЃРѕС…СЂР°РЅРµРЅ Р±РµР· Р±РёС‚С‹С… СЃСЃС‹Р»РѕРє."
                )
            
            try: await status_msg.delete()
            except: pass
            
            await send_long_message(first_msg, md_content, path)
        else:
            await status_msg.edit_text("вќЊ РћС€РёР±РєР°: РќРµ СѓРґР°Р»РѕСЃСЊ РёР·РІР»РµС‡СЊ С‚РµРєСЃС‚ РЅРё РёР· РѕРґРЅРѕРіРѕ РёР·РѕР±СЂР°Р¶РµРЅРёСЏ.")

    except Exception as global_err:
        logging.error(f"РљСЂРёС‚РёС‡РµСЃРєР°СЏ РѕС€РёР±РєР° Р±Р°С‚С‡Р°: {global_err}")
        try:
            error_text = f"вќЊ РљСЂРёС‚РёС‡РµСЃРєР°СЏ РѕС€РёР±РєР° СЃРёСЃС‚РµРјС‹: `{global_err}`"
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
        
        # Р•СЃР»Рё С‚Р°Р№РјРµСЂ СѓР¶Рµ С‚РёРєР°РµС‚ вЂ” СЃР±СЂР°СЃС‹РІР°РµРј РµРіРѕ
        if USER_BATCHES[user_id]['timer_task']:
            USER_BATCHES[user_id]['timer_task'].cancel()
            
        # Р—Р°РїСѓСЃРєР°РµРј РЅРѕРІС‹Р№ С‚Р°Р№РјРµСЂ. 4.5 СЃРµРєСѓРЅРґС‹ С‚РёС€РёРЅС‹ = РєРѕРЅРµС† Р·Р°РіСЂСѓР·РєРё Р°Р»СЊР±РѕРјР°
        USER_BATCHES[user_id]['timer_task'] = asyncio.create_task(
            process_batch_after_delay(user_id, delay=4.5)
        )

# =========================================================================================
# 9. РўРћР§РљРђ Р’РҐРћР”Рђ
# =========================================================================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("рџ‘‹ oxotn1k РіРѕС‚РѕРІ Рє СЂР°Р±РѕС‚Рµ. Р–РґСѓ С‚РІРѕРё РїСЂРѕРјРїС‚С‹ Рё Р°Р»СЊР±РѕРјС‹ (Р»СЋР±РѕРіРѕ СЂР°Р·РјРµСЂР°).", reply_markup=get_kb())

@dp.message(F.text == "рџљЂ Р РµСЃС‚Р°СЂС‚ РєРѕРЅС‚РµР№РЅРµСЂР°")
async def restart_handler(message: Message):
    global LAST_RESTART_TIME
    if message.from_user.id != ADMIN_ID or time.time() - LAST_RESTART_TIME < 10: 
        return
        
    LAST_RESTART_TIME = time.time()
    await message.answer("вЏі РџРµСЂРµР·Р°РіСЂСѓР·РєР° Docker-РєРѕРЅС‚РµР№РЅРµСЂР°...")
    os.system(f"docker restart {CONTAINER_NAME} &")

@dp.message(F.text == "🔄 Переключить шлюз")
async def manual_proxy_switch(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    if len(PROXY_ENDPOINTS) < 2:
        await message.answer("⚠️ Резервный шлюз не задан в настройках Portainer.")
        return
    next_index = next_proxy_index(CURRENT_PROXY_INDEX, len(PROXY_ENDPOINTS))
    candidate = PROXY_ENDPOINTS[next_index]
    status = await message.answer("🔄 Проверяю следующий шлюз перед переключением...")
    try:
        await validate_proxy(candidate.url)
        label = await activate_proxy(next_index)
        await status.edit_text(f"✅ Активирован {label.lower()} шлюз.")
    except Exception as error:
        logging.error("Проверка шлюза не прошла: %s", error)
        await status.edit_text("❌ Переключение отменено: следующий шлюз недоступен.")
async def main():
    logging.info("РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ СЃРёСЃС‚РµРјС‹ (РЎС‚Р°СЂС‚ РґРёР°РіРЅРѕСЃС‚РёРєРё)...")
    diag_report = await check_diagnostics()
    
    try:
        report_text = f"рџљЂ **РљРѕРЅС‚РµР№РЅРµСЂ Р±РѕС‚Р° Р·Р°РїСѓС‰РµРЅ!**\n\nРЎС‚Р°СЂС‚РѕРІР°СЏ РґРёР°РіРЅРѕСЃС‚РёРєР°:\n\n{diag_report}"
        await bot.send_message(ADMIN_ID, report_text, reply_markup=get_kb())
    except Exception as e:
        logging.error(f"РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РїСЂР°РІРёС‚СЊ РїСЂРёРІРµС‚СЃС‚РІРёРµ: {e}")
        
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Р Р°Р±РѕС‚Р° Р±РѕС‚Р° Р·Р°РІРµСЂС€РµРЅР° С€С‚Р°С‚РЅРѕ.")