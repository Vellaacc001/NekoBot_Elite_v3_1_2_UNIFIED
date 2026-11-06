import asyncio
import os
from telethon import TelegramClient

HOME = os.path.expanduser("~")
SESSION_NAME = os.path.join(HOME, "nanora_session")
TARGET_CHAT_ID = -1003909898828

async def debug():
    client = TelegramClient(SESSION_NAME, 37165294, "49dc7b3bfdf9ed434bcebc205595e27b")
    await client.start()
    
    print("Sending test prompt...")
    sent = await client.send_message(TARGET_CHAT_ID, "@nanorabot Who are you?")
    print(f"Sent ID: {sent.id}. Waiting 15s for any message in chat...")
    
    await asyncio.sleep(15)
    
    print("\n--- Recent Messages in Chat ---")
    async for msg in client.iter_messages(TARGET_CHAT_ID, limit=10):
        print(f"ID: {msg.id} | SenderID: {msg.sender_id} | Text: {repr(msg.text)}")
        
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(debug())
