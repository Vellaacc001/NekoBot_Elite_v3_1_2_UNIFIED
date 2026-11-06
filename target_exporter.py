import argparse
import asyncio
import json
import sqlite3
import sys
from hydrogram import Client, filters
from hydrogram.errors import UserAlreadyParticipant, InviteHashInvalid

# Credentials
DEFAULT_BOT_TOKEN = "8120093497:AAGY3NQKGHNnRBxGVwYv-AsKDdHS5zNK98A"

# For User login (+918894878947), Telegram requires API keys generated at https://my.telegram.org
# Replace these with your my.telegram.org keys if logging in as a user account:
USER_API_ID = 37165294
USER_API_HASH = "40dc7b3bfdf9ed434bcebc205595e27b"

# For Bot login, official public fallback credentials work:
BOT_API_ID = 2040
BOT_API_HASH = "b18441a1fe607e10a985b4f1109296f4"

DB_NAME = "telegram_messages.db"

# Target Configuration
INVITE_HASH = "2Z6uKorIDOdkNmY1"
TARGET_USER_ID = 7883544685
TARGET_USERNAME = "You_are_mine_143"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER,
            chat_id INTEGER,
            chat_title TEXT,
            sender_id INTEGER,
            sender_name TEXT,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (message_id, chat_id)
        )
    ''')
    conn.commit()
    conn.close()

def save_message(msg):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    sender_id = msg.from_user.id if msg.from_user else 0
    sender_name = msg.from_user.first_name if msg.from_user else "Unknown"
    chat_title = msg.chat.title or msg.chat.username or "Private"

    cursor.execute('''
        INSERT OR IGNORE INTO messages (message_id, chat_id, chat_title, sender_id, sender_name, text)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        msg.id,
        msg.chat.id,
        chat_title,
        sender_id,
        sender_name,
        msg.text or msg.caption or ''
    ))
    conn.commit()
    conn.close()

def export_to_json(output_file):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT message_id, chat_id, chat_title, sender_id, sender_name, text, timestamp FROM messages')
    rows = cursor.fetchall()
    conn.close()

    data = [
        {
            "message_id": r[0],
            "chat_id": r[1],
            "chat_title": r[2],
            "sender_id": r[3],
            "sender_name": r[4],
            "text": r[5],
            "timestamp": r[6]
        }
        for r in rows
    ]

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Exported {len(data)} messages to {output_file}")

async def main():
    parser = argparse.ArgumentParser(description="Targeted Telegram Message Exporter")
    parser.add_argument("--mode", choices=["bot", "user"], default="bot", help="Authentication mode: 'bot' or 'user'")
    parser.add_argument("--phone", help="Phone number for user mode (e.g., +918894878947)")
    parser.add_argument("--token", default=DEFAULT_BOT_TOKEN, help="Bot token for bot mode")
    parser.add_argument("--export-only", action="store_true", help="Export existing DB to JSON and exit")
    parser.add_argument("--output", default="my_messages.json", help="Output JSON file path")
    args = parser.parse_args()

    init_db()

    if args.export_only:
        export_to_json(args.output)
        sys.exit(0)

    if args.mode == "bot":
        print(f"Initializing in BOT mode using token...")
        app = Client(
            "bot_session",
            api_id=BOT_API_ID,
            api_hash=BOT_API_HASH,
            bot_token=args.token,
            workdir="/data/data/com.termux/files/usr/tmp"
        )
    else:
        print("Initializing in USER mode...")
        app = Client(
            "user_session",
            api_id=USER_API_ID,
            api_hash=USER_API_HASH,
            phone_number=args.phone if args.phone else input("Enter Phone Number (+91...): "),
            workdir="/data/data/com.termux/files/usr/tmp",
            device_model="Redmi 13C 5G",
            system_version="Android 14"
        )

    await app.start()
    me = await app.get_me()
    print(f"Authenticated successfully as: {me.first_name} (@{me.username or 'NoUsername'})")

    if args.mode == "user":
        try:
            await app.join_chat(INVITE_HASH)
            print("Successfully joined target group via invite hash.")
        except UserAlreadyParticipant:
            print("Already in target group.")
        except Exception as e:
            print(f"Group join status: {e}")
    else:
        print("Note: Bot accounts cannot use invite links. Add @{me.username} to the target group manually.")

    @app.on_message()
    async def message_handler(client, message):
        sender_id = message.from_user.id if message.from_user else None
        sender_username = message.from_user.username if message.from_user else ""

        is_target_id = sender_id == TARGET_USER_ID
        is_target_username = sender_username and sender_username.lower() == TARGET_USERNAME.lower()

        if is_target_id or is_target_username:
            try:
                save_message(message)
                print(f"[TARGET DETECTED] Saved msg {message.id} from user {sender_id}")
            except Exception as e:
                print(f"Error saving message: {e}")

    print(f"Listening for messages from @{TARGET_USERNAME} ({TARGET_USER_ID})... Press Ctrl+C to stop.")
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
