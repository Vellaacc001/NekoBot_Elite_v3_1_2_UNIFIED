import sqlite3
import json
import csv
import os

db_name = "telegram_dataset.db"
target_base_name = "You_are_mine_143_Iziiee_7883544685"

print(f"[*] Opening source database: {db_name}")
conn = sqlite3.connect(db_name)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

target_ids = ["7187486402", "7883544685"]
placeholders = ",".join(["?"] * len(target_ids))

# Query messages where sender matches either account ID
query = f"SELECT * FROM messages WHERE sender_username IN ({placeholders}) OR sender_id IN ({placeholders})"
cursor.execute(query, target_ids + target_ids)
rows = cursor.fetchall()

if not rows:
    print("[!] No messages found for the specified IDs in telegram_dataset.db.")
    conn.close()
    exit(1)

print(f"[+] Successfully extracted {len(rows)} combined messages from both accounts.")

# 1. Export as JSONL
jsonl_filename = f"{target_base_name}_dataset.jsonl"
with open(jsonl_filename, "w", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
print(f"[✔] Exported JSONL dataset to: {jsonl_filename}")

# 2. Export as CSV
csv_filename = f"{target_base_name}_dataset.csv"
if rows:
    keys = rows[0].keys()
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    print(f"[✔] Exported CSV dataset to: {csv_filename}")

conn.close()
