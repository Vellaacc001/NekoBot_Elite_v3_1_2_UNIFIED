import sqlite3, os

target = "You_are_mine_143_Iziiee_7883544685.db"
print("Creating/Consolidating master database...")

conn = sqlite3.connect(target)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        chat_id TEXT,
        sender_id TEXT,
        sender_username TEXT,
        message TEXT,
        date TEXT
    )
""")
conn.commit()

total = 0
for db in ["telegram_dataset.db", "telegram_messages.db"]:
    if os.path.exists(db) and db != target:
        print(f"Importing from {db}...")
        try:
            t_conn = sqlite3.connect(db)
            t_cursor = t_conn.cursor()
            t_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            for (table,) in t_cursor.fetchall():
                if "message" in table.lower() or "data" in table.lower():
                    try:
                        t_cursor.execute(f"SELECT * FROM {table}")
                        for row in t_cursor.fetchall():
                            try:
                                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?,?)", row[:6])
                                total += 1
                            except sqlite3.OperationalError:
                                pass
                    except Exception as e:
                        print(f"Error reading {table}: {e}")
            t_conn.close()
        except Exception as e:
            print(f"Error opening {db}: {e}")

conn.commit()
conn.close()
print(f"Done! Total records imported: {total}")
