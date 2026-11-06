import os
import sqlite3
import json
from telethon import TelegramClient

# --- TELEGRAM API CREDENTIALS ---
# Get your api_id and api_hash from https://my.telegram.org
API_ID = 1234567  # Replace with your actual api_id
API_HASH = "your_api_hash_here"  # Replace with your actual api_hash

# --- TARGET USER CONFIGURATION ---
TARGET_NAME = "GALAXY_ANHILATOR"
TARGET_IDS = [5553376334]
TARGET_USERNAMES = ["concyclicity"]

# --- TARGET GROUP CHATS ---
TARGET_CHATS = [
    -1002014292044, # ᴄʜɪᴛ ᴄʜᴀᴛᴛᴇʀѕ
    -1002139578967, # Badmoshi
    -1002005100158, # ᴠɪʙᴇ ʙᴀsᴇ
    -1002403340147, # THe PerFect SlaYers
    -1003587834964, # 𝐒𝐞𝐜𝐫𝐞𝐭 𝐁𝐚𝐬𝐞ᥫ᭡࿐
    -1003119628307, # Unstables
    -1003566685222, # 𝕯ᴇᴀᴅ 𝕻ᴀʀᴀᴅɪsᴇ 🥀
    -1002742171192, # Yay
    -1002591416427  # ＢΛＢΛ ΥΛƓΛ (@Baba_Yaga_World)
]

jsonl_filename = f"MASTER_PERSON_{TARGET_NAME}.jsonl"
db_filename = f"MASTER_PERSON_{TARGET_NAME}.db"

def load_existing_records():
    """Loads existing master records for idempotency / future updates."""
    existing = {}
    if os.path.exists(jsonl_filename):
        with open(jsonl_filename, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    sig = (str(r.get("id")), str(r.get("date")), str(r.get("message")))
                    existing[sig] = r
                except:
                    pass
    return existing

async def main():
    client = TelegramClient('session_extractor', API_ID, API_HASH)
    await client.start()
    print("[+] Connected to Telegram successfully!")

    existing_rows = load_existing_records()
    print(f"[*] Loaded {len(existing_rows)} existing records from master archive.")

    new_fetched_count = 0

    for chat_id in TARGET_CHATS:
        print(f"[*] Scanning chat ID: {chat_id} ...")
        try:
            async for message in client.iter_messages(chat_id):
                sender = await message.get_sender()
                if not sender:
                    continue
                
                sender_id = getattr(sender, 'id', None)
                sender_username = getattr(sender, 'username', '') or ''
                
                # Check if message belongs to target user
                is_match = False
                if sender_id in TARGET_IDS:
                    is_match = True
                elif sender_username and sender_username.lower() in [u.lower() for u in TARGET_USERNAMES]:
                    is_match = True

                if is_match:
                    # Extract full message metadata dictionary
                    row_dict = {
                        "id": str(message.id),
                        "date": str(message.date),
                        "message": str(message.message or ""),
                        "chat_id": str(chat_id),
                        "sender_id": str(sender_id),
                        "sender_username": str(sender_username),
                        "reply_to": str(message.reply_to_msg_id) if message.reply_to else "",
                        "media_type": type(message.media).__name__ if message.media else "",
                        "raw_data": str(message.to_dict())
                    }

                    sig = (row_dict["id"], row_dict["date"], row_dict["message"])
                    if sig not in existing_rows:
                        existing_rows[sig] = row_dict
                        new_fetched_count += 1
        except Exception as e:
            print(f"[-] Error scanning chat {chat_id}: {e}")

    final_rows = list(existing_rows.values())

    # 1. Export to JSONL
    with open(jsonl_filename, "w", encoding="utf-8") as f:
        for r in final_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 2. Export to SQLite DB
    if os.path.exists(db_filename):
        os.remove(db_filename)

    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()

    all_keys = set()
    for r in final_rows:
        all_keys.update(r.keys())
    fieldnames = list(all_keys)

    columns_sql = ", ".join([f'"{col}" TEXT' for col in fieldnames])
    cursor.execute(f"CREATE TABLE IF NOT EXISTS messages ({columns_sql})")

    placeholders = ", ".join(["?" for _ in fieldnames])
    insert_sql = f"INSERT INTO messages ({', '.join([f'\"{c}\"' for c in fieldnames])}) VALUES ({placeholders})"

    for r in final_rows:
        values = [str(r.get(col, "")) for col in fieldnames]
        cursor.execute(insert_sql, values)

    conn.commit()
    conn.close()

    print(f"\n[✔] Extraction complete for {TARGET_NAME}:")
    print(f"    - Newly fetched messages: {new_fetched_count}")
    print(f"    - Total unique master archive size: {len(final_rows)}")
    print(f"    - Saved to: {jsonl_filename} & {db_filename}")

import asyncio
asyncio.run(main())
