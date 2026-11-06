import os
import asyncio
from telethon import TelegramClient

# Configuration details
API_ID = 37165294
API_HASH = "49dc7b3bfdf9ed434bcebc205595e27b"
BOT_TOKEN = "8120093497:AAH1yaIKCRUNo-Ze8ks_yYKLNmd-56vVnls"

# Target Information
TARGET_GC = "@Perfect_Uss"
TARGET_USERNAME = "@You_are_mine_143"
TARGET_USER_ID = 7883544685
MY_USER_ID = 7407659746

# Initialize client as a Bot
client = TelegramClient('bot', API_ID, API_HASH)


async def main():
    print("Connecting to Telegram Bot...")
    # Explicitly pass the bot_token here so it never prompts for input
    await client.start(bot_token=BOT_TOKEN)
    print("Successfully connected as Bot!")

    me = await client.get_me()
    print(f"Logged in as Bot: {me.first_name} (ID: {me.id})")

    try:
        chat = await client.get_entity(TARGET_GC)
        print(f"Group Chat Found: {chat.title} (ID: {chat.id})")
    except Exception as e:
        print(f"Could not find target group: {e}")

    try:
        user = await client.get_entity(TARGET_USERNAME)
        print(
            f"User Found: {user.first_name} (@{user.username}, ID: {user.id})"
        )
    except Exception as e:
        print(f"Could not find target user: {e}")


if __name__ == "__main__":
    asyncio.run(main())
