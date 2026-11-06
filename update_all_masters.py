import os
import sqlite3
import json
import asyncio
from telethon import TelegramClient

API_ID = 37165294
API_HASH = "49dc7b3bfdf9ed434bcebc205595e27b"
SESSION_NAME = "session"

# Master Target Definitions (One dataset per person)
TARGETS = {
    "TANVI": {
        "user_ids": ["7883544685", "7187486402"],
        "usernames": ["You_are_mine_143", "ichiiren", "Iziiee"],
        "jsonl": "TANVI_MASTER.jsonl",
        "db": "TANVI_MASTER.db",
        "chats": "ALL"
    },
    "YASHMEET": {
        "user_ids": ["5553376334"],
        "usernames": ["concyclicity"],
        "jsonl": "YASHMEET_MASTER.jsonl",
        "db": "YASHMEET_MASTER.db",
        "chats": "ALL"
    },
    "SONAL": {
        "user_ids": ["5190868757"],
        "usernames": ["FromPlanet_007897814"],
        "jsonl": "SONAL_MASTER.jsonl",
        "db": "SONAL_MASTER.db",
        "chats": ["ᴄʜɪᴛ ᴄʜᴀᴛᴛᴇʀѕ", "Badmoshi"]
    }
}

TARGET_CHATS = [
    {"name": "ᴄʜɪᴛ ᴄʜᴀᴛᴛᴇʀѕ", "id": -1002014292044},
    {"name": "Badmoshi", "id": -1002139578967},
    {"name": "ᴠɪʙᴇ ʙᴀsᴇ", "id": -1002005100158},
    {"name": "THe PerFect SlaYers", "id": -1002403340147},
    {"name": "𝐒𝐞𝐜𝐫𝐞𝐭 𝐁𝐚𝐬𝐞ᥫ᭡࿐", "id": -1003587834964},
    {"name": "Unstables", "id": -1003119628307},
    {"name": "𝕯ᴇᴀᴅ 𝕻ᴀʀᴀᴅɪsᴇ 🥀", "id": -1003566685222},
    {"name": "Yay", "id": -1002742171192},
    {"name": "ＢΛＢΛ ΥΛƓΛ", "id": -1002591416427},
]

async def main():
    print("[*] Connecting using session 'session'...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("[+] Connected successfully! Starting Master extraction for all targets...\n")

    new_extracted_data = {target_key: [] for target_key in TARGETS}

    for chat in TARGET_CHATS:
        chat_name = chat["name"]
        chat_id = chat["id"]
        print(f"[*] Processing group: {chat_name} (ID: {chat_id})")

        try:
            entity = await client.get_entity(chat_id)
            print("    [+] Loading message history cache...")
            msg_cache = {}
            async for m in client.iter_messages(entity, limit=25000):
                if m and m.id:
                    msg_cache[m.id] = m
            print(f"    [+] Cached {len(msg_cache)} messages. Scanning targets...")

            chat_counts = {k: 0 for k in TARGETS}

            for m_id, message in sorted(msg_cache.items()):
                if not message.sender:
                    continue

                sender_id = str(message.sender_id) if hasattr(message, 'sender_id') else ""
                sender_username = getattr(message.sender, 'username', '') or ""
                sender_firstname = getattr(message.sender, 'first_name', '') or ""
                sender_lastname = getattr(message.sender, 'last_name', '') or ""
                sender_fullname = f"{sender_firstname} {sender_lastname}".strip()

                for target_key, profile in TARGETS.items():
                    # Check if chat is permitted for this target
                    allowed_chats = profile["chats"]
                    if allowed_chats != "ALL" and chat_name not in allowed_chats:
                        continue

                    is_match = (sender_id in profile["user_ids"]) or (sender_username in profile["usernames"])

                    if is_match:
                        parent_id = ""
                        parent_text = ""
                        if message.reply_to and message.reply_to.reply_to_msg_id:
                            p_id = message.reply_to.reply_to_msg_id
                            parent_id = str(p_id)
                            if p_id in msg_cache:
                                parent_text = msg_cache[p_id].text or ""

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

                        new_extracted_data[target_key].append(row_dict)
                        chat_counts[target_key] += 1

            for target_key in TARGETS:
                allowed_chats = profile["chats"]
                if allowed_chats == "ALL" or chat_name in allowed_chats:
                    print(f"    -> [{target_key}] Found {chat_counts[target_key]} entries in {chat_name}")
            print()

        except Exception as e:
            print(f"    [-] Error processing {chat_name}: {e}\n")

    await client.disconnect()

    # --- MERGE & UPDATE MASTER FILES (Zero Data Loss Architecture) ---
    for target_key, profile in TARGETS.items():
        jsonl_file = profile["jsonl"]
        db_file = profile["db"]
        new_rows = new_extracted_data[target_key]

        existing_records = {}
        if os.path.exists(jsonl_file):
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line.strip())
                        r_key = (str(r.get("chat_id")), str(r.get("id")))
                        existing_records[r_key] = r
                    except json.JSONDecodeError:
                        continue

        initial_count = len(existing_records)

        for r in new_rows:
            r_key = (str(r.get("chat_id")), str(r.get("id")))
            existing_records[r_key] = r

        merged_rows = list(existing_records.values())

        with open(jsonl_file, "w", encoding="utf-8") as f:
            for r in merged_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        fieldnames = list(merged_rows[0].keys()) if merged_rows else []
        if fieldnames:
            columns_sql = ", ".join([f'"{col}" TEXT' for col in fieldnames])
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT,
                    date TEXT,
                    message TEXT,
                    parent_message_id TEXT,
                    parent_message_text TEXT,
                    local_chat_flow TEXT,
                    sender_id TEXT,
                    sender_username TEXT,
                    sender_fullname TEXT,
                    chat_id TEXT,
                    chat_title TEXT,
                    PRIMARY KEY (chat_id, id)
                )
            """)

            placeholders = ", ".join(["?" for _ in fieldnames])
            cols_quoted = ", ".join([f'"{c}"' for c in fieldnames])
            insert_sql = f"INSERT OR REPLACE INTO messages ({cols_quoted}) VALUES ({placeholders})"

            for r in merged_rows:
                values = [str(r.get(col, "")) for col in fieldnames]
                cursor.execute(insert_sql, values)

        conn.commit()
        conn.close()

        added_count = len(merged_rows) - initial_count
        print(f"[✔] Master Dataset Updated for {target_key}:")
        print(f"    - Previously stored: {initial_count} records")
        print(f"    - Newly added/updated: {added_count} records")
        print(f"    - Total Master records: {len(merged_rows)}")
        print(f"    - Master JSONL: {jsonl_file}")
        print(f"    - Master SQLite DB: {db_file}\n")

asyncio.run(main())
