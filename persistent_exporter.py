import argparse
import asyncio
import json
import sqlite3
import sys
from telethon import TelegramClient, events

# Insert your new credentials generated for +918894878947
API_ID = NEW_API_ID
API_HASH = "NEW_API_HASH"
DB_NAME = "telegram_messages.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            chat_title TEXT,
            sender_id INTEGER,
            sender_name TEXT,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_message(msg):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO messages (message_id, chat_id, chat_title, sender_id, sender_name, text)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        msg.id,
        msg.chat_id,
        getattr(msg.chat, 'title', getattr(msg.chat, 'username', 'Private')),
        msg.sender_id,
        getattr(msg.sender, 'first_name', '') if msg.sender else 'Unknown',
        msg.text or ''
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
    parser = argparse.ArgumentParser(description="Telegram Message Exporter")
    parser.add_argument("--export-only", action="store_true", help="Export existing DB to JSON and exit")
    parser.add_argument("--output", default="my_messages.json", help="Output JSON file path")
    args = parser.parse_args()

    init_db()

    if args.export_only:
        export_to_json(args.output)
        sys.exit(0)

    client = TelegramClient('exporter_session', API_ID, API_HASH)

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            save_message(event.message)
            print(f"Saved msg {event.message.id} from chat {event.chat_id}")
        except Exception as e:
            print(f"Error saving message: {e}")

    print("Starting Telegram Exporter Client...")
    await client.start()
    print("Listening for new messages... Press Ctrl+C to stop.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
