            await asyncio.sleep(PACE_DELAY)
        except errors.FloodWaitError as e:
            print(f"[!] FloodWait: sleeping {e.seconds + FLOOD_EXTRA_PADDING}s")
            await asyncio.sleep(e.seconds + FLOOD_EXTRA_PADDING)
            continue
        except FATAL_ERRORS as e:
            sys.exit(f"[FATAL] Session invalid: {e}")
        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                raise RuntimeError(f"Phase 2 aborted: {e}")
            print(f"[Error] Retry {consecutive_errors}/{MAX_CONSECUTIVE_ERRORS} in 5s...")
            await asyncio.sleep(5)

    print("[✔] Extraction complete.")


def _secure_session_file(path: str) -> None:
    if os.path.exists(path):
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Persistent Telegram Exporter")
    parser.add_argument("--api-id",   type=int, default=29535685)
    parser.add_argument("--api-hash", type=str, default="05d843a0bfda880a72ca802c341bba74")
    parser.add_argument("--session",  type=str, default="exporter_session")
    parser.add_argument("--chat",     type=str, default="https://t.me/+2Z6uKorIDOdkNmY1")
    parser.add_argument("--target-user", type=int, default=7883544685)
    parser.add_argument("--no-context", action="store_false", dest="context")
    parser.add_argument("--export-only", action="store_true")
    parser.add_argument("--export-user-id", type=int, default=None)
    parser.add_argument("--output", type=str, default="exported_messages.json")
    args = parser.parse_args()

    init_db()

    if args.export_only:
        export_to_json(args.export_user_id, args.output)
        return

    session_file = f"{args.session}.session"
    _secure_session_file(session_file)

    client = TelegramClient(args.session, args.api_id, args.api_hash)
    client.flood_sleep_threshold = 60

    async def runner():
        async with client:
            _secure_session_file(session_file)
            await run_collector(client, args.chat, args.target_user, args.context)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        print("\n[*] Interrupted by user.")
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n[FATAL] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
EOF

pkg install python tmux -y && pip install telethon
chmod +x persistent_exporter.py
termux-wake-lock
tmux new-session -A -s exporter "python persistent_exporter.py"
tmux attach -t exporter
tmux new -s exporter
cat << 'EOF' > persistent_exporter.py
import argparse
import asyncio
import json
import sqlite3
import sys
from telethon import TelegramClient, events

# Replace these with your real values from my.telegram.org
API_ID = 37165294
API_HASH = "40dc7b3bfdf9ed434bcebc205595e27b"
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

    if API_ID == 123456 or API_HASH == "YOUR_API_HASH_HERE":
        print("ERROR: Please edit persistent_exporter.py and enter your actual API_ID and API_HASH.")
        sys.exit(1)

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
EOF

cat << 'EOF' > persistent_exporter.py
import argparse
import asyncio
import json
import sqlite3
import sys
from telethon import TelegramClient, events

# Configuration
API_ID = 37165294
API_HASH = "40dc7b3bfdf9ed434bcebc205595e27b"
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
EOF

python persistent_exporter.py
rm -f exporter_session.session telegram_messages.db
cat << 'EOF' > persistent_exporter.py
import argparse
import asyncio
import json
import sqlite3
import sys
from telethon import TelegramClient, events

API_ID = 37165294
API_HASH = "40dc7b3bfdf9ed434bcebc205595e27b"
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
EOF

python persistent_exporter.py
rm -f exporter_session.session telegram_messages.db
cat << 'EOF' > persistent_exporter.py
import argparse
import asyncio
import json
import sqlite3
import sys
from telethon import TelegramClient, events

API_ID = 37165294
API_HASH = "40dc7b3bfdf9ed434bcebc205595e27b"
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

    # Added explicit device headers to resolve Telethon auth issues
    client = TelegramClient(
        'exporter_session',
        API_ID,
        API_HASH,
        device_model="Android Device",
        system_version="14.0",
        app_version="10.8.1",
        lang_code="en"
    )

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
EOF

python persistent_exporter.py
