import sqlite3
import json
import csv
import os

databases = ["telegram_dataset.db", "You_are_mine_143_Iziiee_7883544685.db"]
all_rows = []
seen_messages = set()
all_keys = set()

for db_name in databases:
    if not os.path.exists(db_name):
        continue
    print(f"[*] Opening and extracting from: {db_name}")
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM messages")
        rows = cursor.fetchall()
        for row in rows:
            row_dict = dict(row)
            all_keys.update(row_dict.keys())
            sig = (row_dict.get("id"), row_dict.get("date"), row_dict.get("message"))
            if sig not in seen_messages:
                seen_messages.add(sig)
                all_rows.append(row_dict)
    except Exception as e:
        print(f"[-] Error reading {db_name}: {e}")
    conn.close()

print(f"[+] Total unique master rows extracted: {len(all_rows)}")

if not all_rows:
    print("[!] No rows found across databases.")
    exit(1)

fieldnames = sorted(list(all_keys))

# Export Master JSONL
jsonl_filename = "You_are_mine_143_Iziiee_7883544685_MASTER_dataset.jsonl"
with open(jsonl_filename, "w", encoding="utf-8") as f:
    for r in all_rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"[✔] Exported Master JSONL to: {jsonl_filename}")

# Export Master CSV with unified fieldnames
csv_filename = "You_are_mine_143_Iziiee_7883544685_MASTER_dataset.csv"
with open(csv_filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
    writer.writeheader()
    for r in all_rows:
        writer.writerow(r)
print(f"[✔] Exported Master CSV to: {csv_filename}")

