import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

# Fetch credentials from environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("Missing API_ID, API_HASH, or BOT_TOKEN in environment variables!")

# Initialize the client with the bot token to prevent interactive login prompts
client = TelegramClient("neko_bot_session", int(API_ID), API_HASH)

async def main():
    print("Starting NekoBot Elite...")
    # Start using the bot token directly
    await client.start(bot_token=BOT_TOKEN)
    print("Bot is up and running!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
