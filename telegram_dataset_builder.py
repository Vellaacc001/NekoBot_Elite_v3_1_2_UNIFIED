# --- Target User & Session Configuration ---
TARGET_USER_ID = 7883544685
TARGET_USER_USERNAME = "@You_are_mine_143"
TARGET_USER_NAME = "Iziiee⋆𐙚"
SESSION_NAME = "You_are_mine_143_Iziiee_7883544685"
# ---------------------------------------------

import argparse
import asyncio
import csv
import json
import sqlite3
import sys
from telethon import TelegramClient, errors

# Configuration details
API_ID = 37165294
API_HASH = "49dc7b3bfdf9ed434bcebc205595e27b"
DB_FILE = "telegram_dataset.db"

BATCH_SIZE = 100
BATCH_DELAY = 1.5


def init_db(db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            msg_id INTEGER,
            chat_id INTEGER,
            chat_title TEXT,
            sender_id INTEGER,
            sender_username TEXT,
            sender_name TEXT,
            message_text TEXT,
            date TEXT,
            reply_to_msg_id INTEGER,
            reply_to_text TEXT,
            reply_to_sender_id INTEGER,
            is_target_msg INTEGER,
            PRIMARY KEY (chat_id, msg_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_progress (
            chat_id INTEGER,
            target_user_id INTEGER,
            lowest_msg_id INTEGER,
            highest_msg_id INTEGER,
            PRIMARY KEY (chat_id, target_user_id)
        )
    """)

    conn.commit()
    conn.close()


def save_message_to_db(msg_data, db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO messages (
            msg_id, chat_id, chat_title, sender_id, sender_username,
            sender_name, message_text, date, reply_to_msg_id,
            reply_to_text, reply_to_sender_id, is_target_msg
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            msg_data["msg_id"],
            msg_data["chat_id"],
            msg_data["chat_title"],
            msg_data["sender_id"],
            msg_data["sender_username"],
            msg_data["sender_name"],
            msg_data["message_text"],
            msg_data["date"],
            msg_data["reply_to_msg_id"],
            msg_data["reply_to_text"],
            msg_data["reply_to_sender_id"],
            msg_data["is_target_msg"],
        ),
    )
    conn.commit()
    conn.close()


def update_progress(chat_id, target_user_id, msg_id, db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT lowest_msg_id, highest_msg_id FROM scrape_progress WHERE chat_id=? AND target_user_id=?",
        (chat_id, target_user_id),
    )
    row = cursor.fetchone()

    if row:
        lowest = min(row[0], msg_id) if row[0] is not None else msg_id
        highest = max(row[1], msg_id) if row[1] is not None else msg_id
    else:
        lowest, highest = msg_id, msg_id

    cursor.execute(
        """
        INSERT INTO scrape_progress (chat_id, target_user_id, lowest_msg_id, highest_msg_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id, target_user_id) DO UPDATE SET
            lowest_msg_id=excluded.lowest_msg_id,
            highest_msg_id=excluded.highest_msg_id
    """,
        (chat_id, target_user_id, lowest, highest),
    )
    conn.commit()
    conn.close()


def get_progress(chat_id, target_user_id, db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fallback check against actual stored messages if checkpoint table is partial
    cursor.execute(
        "SELECT MIN(msg_id), MAX(msg_id) FROM messages WHERE chat_id=?",
        (chat_id,),
    )
    msg_row = cursor.fetchone()

    cursor.execute(
        "SELECT lowest_msg_id, highest_msg_id FROM scrape_progress WHERE chat_id=? AND target_user_id=?",
        (chat_id, target_user_id),
    )
    row = cursor.fetchone()
    conn.close()

    lowest = row[0] if row and row[0] is not None else (msg_row[0] if msg_row else None)
    highest = (
        row[1] if row and row[1] is not None else (msg_row[1] if msg_row else None)
    )

    return lowest, highest


async def parse_msg_metadata(client, message, chat_title, is_target=0):
    sender = await message.get_sender()
    sender_name = (
        f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip()
    )

    reply_to_id = message.reply_to_msg_id if message.reply_to else None
    reply_to_text = None
    reply_to_sender_id = None

    if reply_to_id:
        try:
            parent_msg = await client.get_messages(
                message.peer_id, ids=reply_to_id
            )
            if parent_msg:
                reply_to_text = parent_msg.text
                reply_to_sender_id = parent_msg.sender_id
        except Exception:
            pass

    return {
        "msg_id": message.id,
        "chat_id": message.chat_id,
        "chat_title": chat_title,
        "sender_id": message.sender_id,
        "sender_username": getattr(sender, "username", None),
        "sender_name": sender_name or "Unknown",
        "message_text": message.text or "[Media/Non-text]",
        "date": str(message.date),
        "reply_to_msg_id": reply_to_id,
        "reply_to_text": reply_to_text,
        "reply_to_sender_id": reply_to_sender_id,
        "is_target_msg": is_target,
    }


async def build_dataset(
    client,
    target_chat,
    target_user,
    context_window=2,
    max_messages=200,
    mode="back",
):
    init_db()

    print(f"[*] Resolving Target Chat: {target_chat}")
    try:
        if str(target_chat).lstrip("-").isdigit():
            chat_target = int(target_chat)
            chat_title = str(chat_target)
        else:
            if not target_chat.startswith("@") and not target_chat.startswith("-"):
                resolved_chat = "@" + target_chat
            else:
                resolved_chat = target_chat
            chat_entity_obj = await client.get_entity(resolved_chat)
            chat_target = chat_entity_obj.id
            chat_title = getattr(chat_entity_obj, "title", str(chat_target))
    except Exception as e:
        print(f"[*] Notice: Could not resolve chat entity via get_entity ({e}), falling back to raw: {target_chat}")
        chat_target = target_chat
        chat_title = str(chat_target)

    print(f"[*] Resolving Target User: {target_user}")
    try:
        if str(target_user).lstrip("-").isdigit():
            target_user_id = int(target_user)
            user_entity = None
        else:
            user_entity = await client.get_entity(target_user)
            target_user_id = user_entity.id
    except Exception as e:
        print(f"[*] Notice: Could not resolve entity via get_entity ({e}), falling back to ID matching: {target_user}")
        target_user_id = int(target_user) if str(target_user).lstrip("-").isdigit() else None
        user_entity = None

    lowest_id, highest_id = get_progress(chat_target, target_user_id)
    print(
        f"[*] Saved Checkpoints -> Lowest Saved ID: {lowest_id}, Highest Saved ID: {highest_id}"
    )

    total_extracted = 0

    if mode == "back":
        offset_id = lowest_id if lowest_id else 0
        print(
            f"[*] Running BACKWARD Crawl (fetching history older than ID {offset_id if offset_id else 'Latest'})..."
        )

        while total_extracted < max_messages:
            print(f"[*] Fetching batch (offset_id: {offset_id})...", end="\r")
            try:
                messages = await client.get_messages(
                    chat_target, limit=BATCH_SIZE, offset_id=offset_id
                )
                if not messages:
                    print("[+] Reached the beginning of chat history.")
                    break

                for msg in messages:
                    offset_id = msg.id

                    if msg.sender_id == target_user_id:
                        print(
                            f"[+] Target message found (ID: {msg.id}). Extracting context..."
                        )

                        target_data = await parse_msg_metadata(
                            client, msg, chat_title, is_target=1
                        )
                        save_message_to_db(target_data)

                        surrounding_ids = list(
                            range(
                                max(1, msg.id - context_window),
                                msg.id + context_window + 1,
                            )
                        )
                        if msg.id in surrounding_ids:
                            surrounding_ids.remove(msg.id)

                        flow_messages = await client.get_messages(
                            chat_target, ids=surrounding_ids
                        )
                        for flow_msg in flow_messages:
                            if flow_msg:
                                flow_data = await parse_msg_metadata(
                                    client, flow_msg, chat_title, is_target=0
                                )
                                save_message_to_db(flow_data)

                        total_extracted += 1

                    update_progress(chat_target, target_user_id, msg.id)

                await asyncio.sleep(BATCH_DELAY)

            except errors.FloodWaitError as e:
                print(
                    f"[!] Rate limit hit. Telegram requires waiting {e.seconds}s."
                )
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"[!] Error: {e}")
                break

    elif mode == "forward":
        min_id = highest_id if highest_id else 0
        print(
            f"[*] Running FORWARD Update (fetching new messages newer than ID {min_id})..."
        )

        try:
            async for msg in client.iter_messages(
                chat_target, min_id=min_id, reverse=True
            ):
                if total_extracted >= max_messages:
                    break

                if msg.sender_id == target_user_id:
                    print(
                        f"[+] New Target message found (ID: {msg.id}). Extracting context..."
                    )

                    target_data = await parse_msg_metadata(
                        client, msg, chat_title, is_target=1
                    )
                    save_message_to_db(target_data)

                    surrounding_ids = list(
                        range(
                            max(1, msg.id - context_window),
                            msg.id + context_window + 1,
                        )
                    )
                    if msg.id in surrounding_ids:
                        surrounding_ids.remove(msg.id)

                    flow_messages = await client.get_messages(
                        chat_target, ids=surrounding_ids
                    )
                    for flow_msg in flow_messages:
                        if flow_msg:
                            flow_data = await parse_msg_metadata(
                                client, flow_msg, chat_title, is_target=0
                            )
                            save_message_to_db(flow_data)

                    total_extracted += 1

                update_progress(chat_target, target_user_id, msg.id)

        except errors.FloodWaitError as e:
            print(f"[!] Rate limit hit. Telegram requires waiting {e.seconds}s.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"[!] Error: {e}")

    print(
        f"\n[✔] Extraction finished in '{mode}' mode. Total Target Conversions: {total_extracted}"
    )


def export_dataset(format_type="json", db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM messages ORDER BY chat_id, msg_id DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not rows:
        print("[!] Database is empty. Nothing to export.")
        return

    output_filename = f"extracted_dataset.{format_type}"

    if format_type == "json":
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=4, ensure_ascii=False)
    elif format_type == "csv":
        with open(output_filename, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(
        f"[✔] Successfully exported {len(rows)} records to '{output_filename}'!"
    )


# ==================== SCRIPT ENTRY ====================
async def main():
    parser = argparse.ArgumentParser(
        description="Telegram Context Dataset Extractor"
    )
    parser.add_argument(
        "--chat",
        type=str,
        default="@Perfect_Uss",
        help="Target chat username or ID",
    )
    parser.add_argument(
        "--user",
        type=str,
        default="@You_are_mine_143",
        help="Target user username or ID",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=2,
        help="Surrounding message context window size",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max target messages to extract",
    )
    parser.add_argument(
        "--mode",
        choices=["back", "forward"],
        default="back",
        help="'back' for older history, 'forward' for new messages",
    )
    parser.add_argument(
        "--export",
        type=str,
        choices=["json", "csv"],
        help="Export stored DB to JSON or CSV",
    )

    args = parser.parse_args()

    if args.export:
        export_dataset(args.export)
        return

    client = TelegramClient("session", API_ID, API_HASH)
    await client.start()

    print("=== Telegram Dataset Builder Started ===")
    await build_dataset(
        client,
        target_chat=args.chat,
        target_user=args.user,
        context_window=args.window,
        max_messages=args.limit,
        mode=args.mode,
    )


if __name__ == "__main__":
    asyncio.run(main())
