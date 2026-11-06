import sqlite3
import json
import os

# Define your source databases to pull new logs from
SOURCE_DBS = ["telegram_dataset.db", "You_are_mine_143_Iziiee_7883544685.db"]

# DEFINE YOUR PERSON PROFILES & THEIR MULTI-ACCOUNT ALIASES
# Every ID or username listed here will be merged into ONE single master archive for that person.
PERSON_PROFILES = {
    "Iziiee": {
        "ids": ["7883544685", "You_are_mine_143"],
        "usernames": ["You_are_mine_143_Iziiee"]
    },
    "TargetUser2": {
        "ids": ["7187486402"],
        "usernames": []
    }
}

def load_all_source_rows():
    """Extracts all rows from all source databases with deduplication."""
    all_rows = []
    seen_signatures = set()

    for db in SOURCE_DBS:
        if not os.path.exists(db):
            continue
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM messages")
            for row in cursor.fetchall():
                row_dict = dict(row)
                # Signature to prevent exact duplicate messages
                sig = (row_dict.get("id"), row_dict.get("date"), row_dict.get("message"))
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    all_rows.append(row_dict)
        except Exception as e:
            print(f"[-] Error reading {db}: {e}")
        conn.close()
    return all_rows

def update_or_create_person_master(person_name, aliases, master_rows):
    """Creates or updates a single unified master JSONL and SQLite database for a person."""
    jsonl_filename = f"MASTER_PERSON_{person_name}.jsonl"
    db_filename = f"MASTER_PERSON_{person_name}.db"

    # 1. Load existing records from the person's current master JSONL if it already exists (Future Updates support)
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

    print(f"[*] Processing profile for: {person_name} (Existing master records: {len(existing_rows)})")

    # 2. Filter master rows belonging to this person across all their accounts/aliases
    target_ids = aliases.get("ids", [])
    target_usernames = aliases.get("usernames", [])

    matched_count = 0
    for r in master_rows:
        s_id = str(r.get("sender_id", ""))
        s_user = str(r.get("sender_username", ""))
        from_id = str(r.get("from_id", ""))
        combined_str = f"{s_id} {s_user} {from_id}"

        # Check if any ID or username matches this person's aliases
        is_match = False
        for uid in target_ids:
            if uid and uid in combined_str:
                is_match = True
                break
        if not is_match:
            for uname in target_usernames:
                if uname and uname in combined_str:
                    is_match = True
                    break

        if is_match:
            sig = (r.get("id"), r.get("date"), r.get("message"))
            if sig not in existing_rows:
                existing_rows[sig] = r
                matched_count += 1

    final_rows = list(existing_rows.values())

    # 3. Export Unified Master JSONL (Preserving all metadata)
    with open(jsonl_filename, "w", encoding="utf-8") as f:
        for r in final_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 4. Export Unified Master SQLite Database
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

    print(f"[✔] Master archive updated for '{person_name}':")
    print(f"    - Added {matched_count} new messages (Total unique archive: {len(final_rows)} messages)")
    print(f"    - JSONL: {jsonl_filename}")
    print(f"    - SQLite DB: {db_filename}\n")

# --- MAIN EXECUTION ---
print("[*] Loading raw records from all source databases...")
all_master_rows = load_all_source_rows()
print(f"[+] Loaded {len(all_master_rows)} total source rows across databases.\n")

for name, profile_aliases in PERSON_PROFILES.items():
    update_or_create_person_master(name, profile_aliases, all_master_rows)

print("[✔] All person-specific master archives are updated and fully synchronized!")
