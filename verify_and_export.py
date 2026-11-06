import os
import sqlite3
import json
import csv

target_base_name = "You_are_mine_143_Iziiee_7883544685"
db_name = f"{target_base_name}.db"

print(f"[*] Using target database: {db_name}")
if not os.path.exists(db_name):
    print(f"[!] Database file '{db_name}' not found!")
    exit(1)

conn = sqlite3.connect(db_name)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

target_ids = [7187486402, 7883544685]
placeholders = ",".join(["?"] * len(target_ids))

query = f"SELECT * FROM messages WHERE sender_id IN ({placeholders})"
cursor.execute(query, target_ids)
rows = cursor.fetchall()

if not rows:
    print("[!] No messages found matching the target user IDs in this database.")
    conn.close()
    exit(1)

print(f"[+] Found {len(rows)} total messages across both accounts.")

# 1. Export as JSONL
jsonl_filename = f"{target_base_name}_dataset.jsonl"
with open(jsonl_filename, "w", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
print(f"[✔] Exported JSONL to: {jsonl_filename}")

# 2. Export as CSV
csv_filename = f"{target_base_name}_dataset.csv"
if rows:
    keys = rows[0].keys()
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    print(f"[✔] Exported CSV to: {csv_filename}")

conn.close()
