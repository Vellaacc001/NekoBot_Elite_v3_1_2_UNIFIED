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

jsonl_filename = "MASTER_PERSON_GALAXY_ANHILATOR_CONTEXTUAL.jsonl"
db_filename = "MASTER_PERSON_GALAXY_ANHILATOR_CONTEXTUAL.db"

async def main():
    print(f"[*] Connecting using session '{SESSION_NAME}'...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("[+] Connected successfully! Starting contextual extraction...\n")

    extracted_rows = []

    for chat in TARGET_CHATS:
        chat_name = chat["name"]
        chat_id = chat["id"]
        print(f"[*] Processing group: {chat_name}")
        
        try:
            entity = await client.get_entity(chat_id)
            count = 0
            
            async for message in client.iter_messages(entity, reverse=False):
                if not message.sender:
                    continue
                
                sender_id = str(message.sender_id) if hasattr(message, 'sender_id') else ""
                sender_username = getattr(message.sender, 'username', '') or ""
                
                is_match = (sender_id in TARGET_USER_IDS) or (sender_username in TARGET_USER_USERNAMES)
                
                if is_match:
                    parent_text = ""
                    parent_id = ""
                    
                    # Check if message is a reply to another message
                    if message.reply_to and message.reply_to.reply_to_msg_id:
                        parent_id = str(message.reply_to.reply_to_msg_id)
                        try:
                            parent_msg = await client.get_messages(entity, ids=int(parent_id))
                            if parent_msg and parent_msg.text:
                                parent_text = parent_msg.text
                        except Exception:
                            pass # Parent message might be deleted or inaccessible
                    
                    row_dict = {
                        "id": str(message.id),
                        "date": str(message.date),
                        "message": message.text or "",
                        "parent_message_id": parent_id,
                        "parent_message_text": parent_text,
                        "sender_id": sender_id,
                        "sender_username": sender_username,
                        "chat_id": str(chat_id),
                        "chat_title": chat_name,
                    }
                    
                    extracted_rows.append(row_dict)
                    count += 1
                    if count % 100 == 0:
                        print(f"    ... processed {count} matching contextual messages ...")
                        
            print(f"    [✔] Finished {chat_name}: Found {count} matching messages with context.\n")
        except Exception as e:
            print(f"    [-] Error processing {chat_name}: {e}\n")

    await client.disconnect()

    # Export Unified Master JSONL with Context
    with open(jsonl_filename, "w", encoding="utf-8") as f:
        for r in extracted_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Export Unified Master SQLite Database with Context
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

    print(f"[✔] Contextual Master archive successfully created:")
    print(f"    - Total records: {len(extracted_rows)}")
    print(f"    - JSONL: {jsonl_filename}")
    print(f"    - SQLite DB: {db_filename}\n")

asyncio.run(main())
