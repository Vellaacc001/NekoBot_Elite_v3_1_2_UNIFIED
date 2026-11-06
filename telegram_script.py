import os
import asyncio
from telethon import TelegramClient

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

print(f"DEBUG Check -> API_ID: {bool(API_ID)}, API_HASH: {bool(API_HASH)}, BOT_TOKEN: {bool(BOT_TOKEN)}")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("Missing API_ID, API_HASH, or BOT_TOKEN in environment variables! Check your GitHub Repository Secrets.")

client = TelegramClient("neko_bot_session", int(API_ID), API_HASH)

async def main():
    print("Starting NekoBot Elite...")
    await client.start(bot_token=BOT_TOKEN)
    print("Bot is up and running successfully!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
