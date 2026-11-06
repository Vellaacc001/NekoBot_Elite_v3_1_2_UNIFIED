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

# Top 5 core target groups for maximum extraction
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
    if os.path.exists(jsonl_filename):
        with open(jsonl_filename, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    sig = (r.get("id"), r.get("date"), r.get("message"))
                    existing_rows[sig] = r
                except:
                    pass

    print(f"[*] Connecting using session '{SESSION_NAME}'...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("[+] Connected successfully! Starting maximum extraction...\n")

    extracted_rows = []
    seen_sigs = set(existing_rows.keys())

    for chat in TARGET_CHATS:
        chat_name = chat["name"]
        chat_id = chat["id"]
        print(f"[*] Extracting group: {chat_name} ({chat_id})")
        try:
            entity = await client.get_entity(chat_id)
            count = 0
            scanned = 0
            
            # Unlimited scan with automatic FloodWait handling
            while True:
                try:
                    async for message in client.iter_messages(entity, offset_id=0, reverse=False):
                        scanned += 1
                        if scanned % 1000 == 0:
                            print(f"    ... parsed {scanned} messages ...")
                        
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
            
            print(f"    [✔] Done! Found {count} matching messages out of {scanned} total messages scanned in {chat_name}\n")
        except Exception as e:
            print(f"    [-] Error extracting {chat_name}: {e}\n")

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
    print(f"    - Added {len(extracted_rows)} new messages (Total archive size: {len(final_rows)} messages)")
    print(f"    - JSONL: {jsonl_filename}")
    print(f"    - SQLite DB: {db_filename}\n")

asyncio.run(main())
