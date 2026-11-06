import os
import sqlite3
import json
import asyncio
from telethon import TelegramClient
from telethon.errors import FloodWaitError

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

jsonl_filename = "MASTER_PERSON_GALAXY_ANHILATOR.jsonl"
db_filename = "MASTER_PERSON_GALAXY_ANHILATOR.db"

async def main():
    existing_rows = {}
    chat_min_ids = {chat["id"]: float('inf') for chat in TARGET_CHATS}

    if os.path.exists(jsonl_filename):
        with open(jsonl_filename, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    sig = (r.get("id"), r.get("date"), r.get("message"))
                    existing_rows[sig] = r
                    
                    c_id = int(r.get("chat_id", 0))
                    m_id = int(r.get("id", 0))
                    if c_id in chat_min_ids and m_id < chat_min_ids[c_id]:
                        chat_min_ids[c_id] = m_id
                except:
                    pass

    print(f"[*] Connecting using session '{SESSION_NAME}'...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("[+] Connected successfully! Starting deep historical extraction backwards...\n")

    extracted_rows = []
    seen_sigs = set(existing_rows.keys())

    for chat in TARGET_CHATS:
        chat_name = chat["name"]
        chat_id = chat["id"]
        
        # Determine starting offset (lowest message ID we already have, or start from 0/latest)
        current_min = chat_min_ids.get(chat_id, float('inf'))
        offset_id = current_min if current_min != float('inf') else 0
        
        print(f"[*] Deep scanning group: {chat_name} (Starting from message ID < {offset_id if offset_id else 'Latest'})")
        try:
            entity = await client.get_entity(chat_id)
            count = 0
            scanned = 0
            
            while True:
                batch_count = 0
                oldest_in_batch = None
                
                while True:
                    try:
                        # Fetch messages older than offset_id (iterating backwards in history)
                        async for message in client.iter_messages(entity, offset_id=offset_id, limit=1000, reverse=False):
                            scanned += 1
                            batch_count += 1
                            m_id = message.id
                            
                            if oldest_in_batch is None or m_id < oldest_in_batch:
                                oldest_in_batch = m_id
                            
                            if not message.sender:
                                continue
                            
                            sender_id = str(message.sender_id) if hasattr(message, 'sender_id') else ""
                            sender_username = getattr(message.sender, 'username', '') or ""
                            
                            is_match = (sender_id in TARGET_USER_IDS) or (sender_username in TARGET_USER_USERNAMES)
                            
                            if is_match:
                                row_dict = {
                                    "id": str(message.id),
                                    "date": str(message.date),
                                    "message": message.text or "",
                                    "sender_id": sender_id,
                                    "sender_username": sender_username,
                                    "chat_id": str(chat_id),
                                    "chat_title": chat_name,
                                    "reply_to_message_id": str(message.reply_to.reply_to_msg_id) if message.reply_to else "",
                                    "views": str(getattr(message, 'views', '')),
                                    "forwards": str(getattr(message, 'forwards', '')),
                                }
                                
                                sig = (row_dict.get("id"), row_dict.get("date"), row_dict.get("message"))
                                if sig not in seen_sigs:
                                    seen_sigs.add(sig)
                                    existing_rows[sig] = row_dict
                                    extracted_rows.append(row_dict)
                                    count += 1
                        break
                    except FloodWaitError as e:
                        print(f"    [!] Rate limit hit. Sleeping for {e.seconds} seconds...")
                        await asyncio.sleep(e.seconds)

                if batch_count == 0 or oldest_in_batch is None or oldest_in_batch <= 1:
                    break
                
                offset_id = oldest_in_batch
                print(f"    ... reached deeper history (older than ID {offset_id}, scanned {scanned} total) ...")
                await asyncio.sleep(0.5) # Gentle pause between historical batches

            print(f"    [✔] Deep scan complete for {chat_name}. Found {count} additional matching messages.\n")
        except Exception as e:
            print(f"    [-] Error in deep scan for {chat_name}: {e}\n")

    await client.disconnect()

    final_rows = list(existing_rows.values())

    # Export Unified Master JSONL
    with open(jsonl_filename, "w", encoding="utf-8") as f:
        for r in final_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Export Unified Master SQLite Database
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

    print(f"[✔] Master archive successfully updated for GALAXY ANHILATOR (@concyclicity):")
    print(f"    - Added {len(extracted_rows)} older messages (Total archive size: {len(final_rows)} messages)")
    print(f"    - JSONL: {jsonl_filename}")
    print(f"    - SQLite DB: {db_filename}\n")

asyncio.run(main())
