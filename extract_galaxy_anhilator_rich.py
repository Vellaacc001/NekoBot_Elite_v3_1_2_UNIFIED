import os
import sqlite3
import json
import asyncio
from telethon import TelegramClient

# --- CONFIGURATION ---
API_ID = 37165294
API_HASH = "49dc7b3bfdf9ed434bcebc205595e27b"
SESSION_NAME = "session"

TARGET_USER_IDS = ["5553376334"]
TARGET_USER_USERNAMES = ["concyclicity"]

TARGET_CHATS = [
    {"name": "ᴄʜɪᴛ ᴄʜᴀᴛᴛᴇʀѕ", "id": -1002014292044},
    {"name": "Badmoshi", "id": -1002139578967},
    {"name": "ᴠɪʙᴇ ʙᴀsᴇ", "id": -1002005100158},
    {"name": "THe PerFect SlaYers", "id": -1002403340147},
    {"name": "𝐒𝐞𝐜𝐫𝐞𝐭 𝐁𝐚𝐬𝐞ᥫ᭡࿐", "id": -1003587834964},
]

jsonl_filename = "MASTER_PERSON_GALAXY_ANHILATOR_RICH.jsonl"
db_filename = "MASTER_PERSON_GALAXY_ANHILATOR_RICH.db"

async def main():
    print(f"[*] Connecting using session '{SESSION_NAME}'...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("[+] Connected successfully! Starting high-speed rich extraction...\n")

    extracted_rows = []

    for chat in TARGET_CHATS:
        chat_name = chat["name"]
        chat_id = chat["id"]
        print(f"[*] Processing group: {chat_name}")

        try:
            entity = await client.get_entity(chat_id)
            
            # 1. Bulk fetch messages into memory dictionary for instant context lookup (fastest approach)
            print(f"    [+] Loading message history into memory cache...")
            msg_cache = {}
            async for m in client.iter_messages(entity, limit=10000): # Adjust limit if needed per group
                if m and m.id:
                    msg_cache[m.id] = m
            print(f"    [+] Cached {len(msg_cache)} messages. Scanning for targets...")

            count = 0
            for m_id, message in sorted(msg_cache.items()):
                if not message.sender:
                    continue

                sender_id = str(message.sender_id) if hasattr(message, 'sender_id') else ""
                sender_username = getattr(message.sender, 'username', '') or ""
                sender_firstname = getattr(message.sender, 'first_name', '') or ""
                sender_lastname = getattr(message.sender, 'last_name', '') or ""
                sender_fullname = f"{sender_firstname} {sender_lastname}".strip()

                is_match = (sender_id in TARGET_USER_IDS) or (sender_username in TARGET_USER_USERNAMES)

                if is_match:
                    # Parent message extraction (instant lookup from cache)
                    parent_id = ""
                    parent_text = ""
                    if message.reply_to and message.reply_to.reply_to_msg_id:
                        p_id = message.reply_to.reply_to_msg_id
                        parent_id = str(p_id)
                        if p_id in msg_cache:
                            parent_text = msg_cache[p_id].text or ""

                    # Immediate chat flow (3 messages before and 3 messages after)
                    context_window = []
                    for offset in range(-3, 4):
                        neighbor_id = m_id + offset
                        if neighbor_id in msg_cache and neighbor_id != m_id:
                            nbr = msg_cache[neighbor_id]
                            nbr_sender = getattr(nbr.sender, 'username', '') or str(nbr.sender_id) if nbr.sender else "unknown"
                            context_window.append({
                                "id": str(nbr.id),
                                "sender": nbr_sender,
                                "text": nbr.text or ""
                            })

                    row_dict = {
                        "id": str(message.id),
                        "date": str(message.date),
                        "message": message.text or "",
                        "parent_message_id": parent_id,
                        "parent_message_text": parent_text,
                        "local_chat_flow": json.dumps(context_window, ensure_ascii=False),
                        "sender_id": sender_id,
                        "sender_username": sender_username,
                        "sender_fullname": sender_fullname,
                        "chat_id": str(chat_id),
                        "chat_title": chat_name,
                    }

                    extracted_rows.append(row_dict)
                    count += 1

            print(f"    [✔] Finished {chat_name}: Found {count} rich contextual entries.\n")
        except Exception as e:
            print(f"    [-] Error processing {chat_name}: {e}\n")

    await client.disconnect()

    # Export Unified Master JSONL
    with open(jsonl_filename, "w", encoding="utf-8") as f:
        for r in extracted_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Export Unified Master SQLite Database
    if os.path.exists(db_filename):
        os.remove(db_filename)

    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()

    fieldnames = list(extracted_rows[0].keys()) if extracted_rows else []
    if fieldnames:
        columns_sql = ", ".join([f'"{col}" TEXT' for col in fieldnames])
        cursor.execute(f"CREATE TABLE IF NOT EXISTS messages ({columns_sql})")

        placeholders = ", ".join(["?" for _ in fieldnames])
        insert_sql = f"INSERT INTO messages ({', '.join([f'\"{c}\"' for c in fieldnames])}) VALUES ({placeholders})"

        for r in extracted_rows:
            values = [str(r.get(col, "")) for col in fieldnames]
            cursor.execute(insert_sql, values)

    conn.commit()
    conn.close()

    print(f"[✔] Rich Contextual Master archive successfully created:")
    print(f"    - Total records: {len(extracted_rows)}")
    print(f"    - JSONL: {jsonl_filename}")
    print(f"    - SQLite DB: {db_filename}\n")

asyncio.run(main())
