import asyncio
from telethon import TelegramClient

# Configuration details
API_ID = 37165294
API_HASH = "49dc7b3bfdf9ed434bcebc205595e27b"

# Target Information
TARGET_GC = "@Perfect_Uss"
TARGET_USERNAME = "@You_are_mine_143"
TARGET_USER_ID = 7883544685
MY_USER_ID = 7407659746

# Initialize client
client = TelegramClient("my_account", API_ID, API_HASH)


async def main():
    print("Connecting to Telegram...")
    await client.start()
    print("Successfully connected!")

    me = await client.get_me()
    print(f"Logged in as: {me.first_name} (ID: {me.id})")

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
    with client:
        client.loop.run_until_complete(main())

