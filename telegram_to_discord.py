print("[DEBUG] Script partito")
import sys
sys.stdout.flush()# === telegram_to_discord.py ===



import os
import asyncio
import aiohttp
from io import BytesIO
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto
import cloudinary
import cloudinary.uploader
import nest_asyncio

nest_asyncio.apply()

LAST_ID_FILE = 'last_id.txt'

api_id = int(os.environ.get("TELEGRAM_API_ID"))
api_hash = os.environ.get("TELEGRAM_API_HASH")
phone_number = os.environ.get("TELEGRAM_PHONE")
target_group = 'tioconsigliagiochi'

discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

client = TelegramClient('sessione_unica', api_id, api_hash)

async def send_to_discord(text):
    async with aiohttp.ClientSession() as session:
        payload = {"content": text}
        async with session.post(discord_webhook_url, json=payload) as resp:
            print(f"[Discord] Status: {resp.status}")
            sys.stdout.flush()

async def upload_to_cloudinary(buffer, filename, is_video=False):
    buffer.seek(0)
    try:
        result = cloudinary.uploader.upload_large(
            buffer,
            resource_type="video" if is_video else "image",
            public_id=filename,
            chunk_size=6 * 1024 * 1024
        )
        return result['secure_url']
    except Exception as e:
        print(f"[Cloudinary] Upload error: {e}")
        sys.stdout.flush()
        return None

def read_last_id():
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, 'r') as f:
            return int(f.read())
    return 0

def save_last_id(last_id):
    with open(LAST_ID_FILE, 'w') as f:
        f.write(str(last_id))

async def process_messages():
    print("[Telegram] Avvio client...")
    sys.stdout.flush()
    await client.start(phone=phone_number)
    last_id = read_last_id()
    print(f"[Telegram] Ultimo ID processato: {last_id}")
    sys.stdout.flush()

    async for message in client.iter_messages(target_group, min_id=last_id):
        parts = []
        separator = "\n⭒☆━━━━━━━━━━━━━━━━━━━━━━━━☆⭒\n"
        
        if message.message:
            parts.append(f"📄 {message.message}")

        if message.media:
            buffer = BytesIO()
            filename = f"media_{message.id}"
            try:
                await client.download_media(message.media, file=buffer)
                mime = message.file.mime_type if message.file else ""

                if 'video' in mime:
                    url = await upload_to_cloudinary(buffer, filename, is_video=True)
                    if url:
                        parts.append(f"📹 {url}")
                elif 'image' in mime or isinstance(message.media, MessageMediaPhoto):
                    url = await upload_to_cloudinary(buffer, filename, is_video=False)
                    if url:
                        parts.append(f"🖼️ {url}")
                else:
                    print(f"[Telegram] Tipo file non gestito: {mime}")
                    sys.stdout.flush()
            except Exception as e:
                print(f"[Telegram] Errore download/upload: {e}")
                sys.stdout.flush()

        if parts:
            msg = separator + "\n".join(parts) + separator
            await send_to_discord(msg)
            save_last_id(message.id)

    print("[Telegram] Completato!")
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(process_messages())
