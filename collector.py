import asyncio
from telethon import TelegramClient, events

API_ID = 37165294
API_HASH = "49dc7b3bfdf9ed434bcebc205595e27b"
TARGET_CHAT_ID = -1003909898828
NANORA_USER_ID = 6883478130

client = TelegramClient("nanora_session", API_ID, API_HASH)

@client.on(events.NewMessage(chats=TARGET_CHAT_ID))
async def handler(event):
    sender = await event.get_sender()
    sender_name = sender.first_name if sender else "Unknown"
    
    if event.sender_id == NANORA_USER_ID:
        print(f"\n[NANORA RESPONDED]:\n{event.text}\n" + "-"*40)
    else:
        print(f"[{sender_name}]: {event.text}")

async def main():
    print(f"\nListening for Nanora in 'xiurz' (ID: {TARGET_CHAT_ID})...\nPress Ctrl+C to stop.\n")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
