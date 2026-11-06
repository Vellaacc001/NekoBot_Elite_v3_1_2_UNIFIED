#!/usr/bin/env python3
"""
Collect messages from multiple target users in Telegram group chats.
Built for personality-modeling dataset construction from group conversations.

- Single pass per chat, filtered to a set of target user IDs
- Per-chat checkpointing for resumable backfill
- WAL mode for Termux crash safety
- FloodWait-aware, FATAL session error short-circuit
- Surrounding-context capture for each target message
- JSON export filtered by user ID
"""
import argparse
import asyncio
import json
import os
import re
import sqlite3
import sys

from telethon import TelegramClient, errors
from telethon.tl.functions.messages import (
    CheckChatInviteRequest, ImportChatInviteRequest,
)

# ==================== CONFIG ====================
API_ID = 37165294                    # <-- replace with your NEW id from my.telegram.org
API_HASH = "40dc7b3bfdf9ed434bcebc205595e27b"   # <-- replace with your NEW hash
SESSION = "exporter_session"
DB_FILE = "telegram_messages.db"

# Your friend (target of the dataset) and you (for conversational context)
TARGET_USERS = [
    7883544685,   # friend  @You_are_mine_143
    7407659746,   # you
]

# Group chat(s) to scrape
TARGET_CHATS = [
    "https://t.me/+2Z6uKorIDOdkNmY1",
]

BATCH_SIZE = 100
PACE_DELAY = 1.0
CONTEXT_BEFORE = 3
CONTEXT_AFTER = 3
# ================================================

FATAL_ERRORS = (
    errors.AuthKeyUnregisteredError,
    errors.UserDeactivatedError,
    errors.SessionRevokedError,
    errors.AuthKeyDuplicatedError,
)

# ---------------- DB ----------------
def get_conn():
    c = sqlite3.connect(DB_FILE, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA synchronous=NORMAL;")
    c.execute("PRAGMA busy_timeout=10000;")
    return c

def init_db():
    c = get_conn()
    try:
        with c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    sender_id INTEGER,
                    sender_name TEXT,
                    timestamp TEXT,
                    text TEXT,
                    reply_to_msg_id INTEGER,
                    context_json TEXT,
                    PRIMARY KEY (chat_id, message_id)
                );
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_sender ON messages(sender_id, timestamp);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_chat ON messages(chat_id, message_id);")
    finally:
        c.close()

def chat_bounds(chat_id):
    c = get_conn()
    try:
        cur = c.cursor()
        cur.execute("SELECT MIN(message_id), MAX(message_id) FROM messages WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return (row[0], row[1]) if row and row[0] is not None else (None, None)
    finally:
        c.close()

def save_batch(records):
    if not records:
        return True
    c = get_conn()
    try:
        c.execute("BEGIN")
        c.executemany("""
            INSERT OR REPLACE INTO messages
            (chat_id, message_id, sender_id, sender_name, timestamp,
             text, reply_to_msg_id, context_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        c.commit()
        return True
    except Exception as e:
        c.rollback()
        print(f"[DB error] {e}")
        return False
    finally:
        c.close()

# ---------------- Entity resolution ----------------
async def resolve_chat(client, raw):
    raw = str(raw).strip()
    m = re.match(r"https?://t\.me/\+([A-Za-z0-9_-]+)", raw)
    if m:
        h = m.group(1)
        try:
            chk = await client(CheckChatInviteRequest(h))
            if getattr(chk, "chat", None):
                return chk.chat
            imp = await client(ImportChatInviteRequest(h))
            return imp.chats[0]
        except Exception as e:
            print(f"[!] invite resolve failed: {e}")
            return None
    if raw.lstrip("-").isdigit():
        try:
            return await client.get_entity(int(raw))
        except Exception as e:
            print(f"[!] entity resolve failed: {e}")
            return None
    try:
        return await client.get_entity(raw)
    except Exception as e:
        print(f"[!] entity resolve failed: {e}")
        return None

SENDER_CACHE = {}

async def sender_name(client, sid):
    if not sid:
        return "Unknown"
    if sid in SENDER_CACHE:
        return SENDER_CACHE[sid]
    try:
        e = await client.get_entity(sid)
        f = getattr(e, "first_name", "") or ""
        l = getattr(e, "last_name", "") or ""
        n = f"{f} {l}".strip() or getattr(e, "title", "") or f"User_{sid}"
    except Exception:
        n = f"User_{sid}"
    SENDER_CACHE[sid] = n
    return n

# ---------------- Context ----------------
async def fetch_context(client, chat_entity, msg):
    out = []
    try:
        before = [m async for m in client.iter_messages(chat_entity, limit=CONTEXT_BEFORE, max_id=msg.id)]
        before.reverse()
        for m in before:
            out.append({
                "message_id": m.id,
                "sender_id": m.sender_id,
                "sender_name": await sender_name(client, m.sender_id),
                "text": m.text or "",
                "timestamp": m.date.isoformat() if m.date else None,
            })
        async for m in client.iter_messages(chat_entity, limit=CONTEXT_AFTER, min_id=msg.id, reverse=True):
            out.append({
                "message_id": m.id,
                "sender_id": m.sender_id,
                "sender_name": await sender_name(client, m.sender_id),
                "text": m.text or "",
                "timestamp": m.date.isoformat() if m.date else None,
            })
    except Exception as e:
        print(f"[!] context fetch failed for msg {msg.id}: {e}")
    return json.dumps(out, ensure_ascii=False)

# ---------------- Scrape ----------------
async def scrape_chat(client, chat_entity, target_set):
    chat_id = chat_entity.id
    title = getattr(chat_entity, "title", None) or getattr(chat_entity, "username", None) or str(chat_id)
    print(f"\n=== {title} ({chat_id}) ===")

    min_id, max_id = chat_bounds(chat_id)
    print(f"[*] checkpoint: {min_id} .. {max_id}" if min_id else "[*] fresh start")

    batch = []

    async def flush():
        if not batch:
            return True
        if save_batch(list(batch)):
            print(f"  [+] saved {len(batch)}")
            batch.clear()
            return True
        return False

    async def record(m):
        ctx = await fetch_context(client, chat_entity, m)
        batch.append((
            chat_id, m.id, m.sender_id,
            await sender_name(client, m.sender_id),
            m.date.isoformat() if m.date else "",
            m.text, m.reply_to_msg_id, ctx,
        ))

    # Phase 1: forward catch-up
    if max_id is not None:
        print("[*] phase 1: forward catch-up")
        cursor = max_id
        consecutive = 0
        while True:
            try:
                async for m in client.iter_messages(chat_entity, min_id=cursor, reverse=True):
                    cursor = m.id
                    if m.sender_id in target_set and m.text:
                        await record(m)
                        if len(batch) >= BATCH_SIZE:
                            if not await flush():
                                sys.exit("[FATAL] DB failure")
                            await asyncio.sleep(PACE_DELAY)
                if not await flush():
                    sys.exit("[FATAL] final phase-1 flush failed")
                print("[+] phase 1 done")
                break
            except errors.FloodWaitError as e:
                print(f"[FloodWait] {e.seconds}s"); await asyncio.sleep(e.seconds + 2)
            except FATAL_ERRORS as e:
                sys.exit(f"[FATAL] {e}")
            except Exception as e:
                consecutive += 1
                if consecutive >= 5:
                    raise
                print(f"[retry {consecutive}/5] {e}"); await asyncio.sleep(5)

    # Phase 2: historical backfill
    print("[*] phase 2: historical backfill")
    offset = min_id if min_id is not None else 0
    consecutive = 0
    while True:
        try:
            fetched = 0
            kwargs = {"limit": BATCH_SIZE}
            if offset > 0:
                kwargs["max_id"] = offset
            async for m in client.iter_messages(chat_entity, **kwargs):
                fetched += 1
                offset = m.id
                if m.sender_id in target_set and m.text:
                    await record(m)
                    if len(batch) >= BATCH_SIZE:
                        if not await flush():
                            sys.exit("[FATAL] DB failure")
                        await asyncio.sleep(PACE_DELAY)
            if not await flush():
                sys.exit("[FATAL] final phase-2 flush failed")
            if fetched == 0:
                print("[+] phase 2 done")
                break
            await asyncio.sleep(PACE_DELAY)
        except errors.FloodWaitError as e:
            print(f"[FloodWait] {e.seconds}s"); await asyncio.sleep(e.seconds + 2)
        except FATAL_ERRORS as e:
            sys.exit(f"[FATAL] {e}")
        except Exception as e:
            consecutive += 1
            if consecutive >= 5:
                raise
            print(f"[retry {consecutive}/5] {e}"); await asyncio.sleep(5)

# ---------------- Export ----------------
def export(target_ids=None, output="my_messages.json"):
    c = get_conn()
    try:
        cur = c.cursor()
        if target_ids:
            ph = ",".join("?" * len(target_ids))
            cur.execute(f"""
                SELECT chat_id, message_id, sender_id, sender_name,
                       timestamp, text, reply_to_msg_id, context_json
                FROM messages WHERE sender_id IN ({ph})
                ORDER BY timestamp ASC
            """, tuple(target_ids))
        else:
            cur.execute("""
                SELECT chat_id, message_id, sender_id, sender_name,
                       timestamp, text, reply_to_msg_id, context_json
                FROM messages ORDER BY timestamp ASC
            """)
        rows = cur.fetchall()
    finally:
        c.close()

    data = [{
        "chat_id": r[0], "message_id": r[1], "sender_id": r[2],
        "sender_name": r[3], "timestamp": r[4], "text": r[5],
        "reply_to_msg_id": r[6],
        "context": json.loads(r[7]) if r[7] else [],
    } for r in rows]

    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[+] exported {len(data)} messages to {output}")

# ---------------- Main ----------------
async def main_async(args):
    client = TelegramClient(args.session, args.api_id, args.api_hash)
    client.flood_sleep_threshold = 60
    await client.start()

    targets = set(args.target_user) if args.target_user else set(TARGET_USERS)
    chats = args.chat if args.chat else TARGET_CHATS

    if not targets:
        sys.exit("[FATAL] no target users. Set TARGET_USERS or pass --target-user.")

    print(f"[*] targets: {sorted(targets)}")
    print(f"[*] chats: {chats}")

    for c in chats:
        ent = await resolve_chat(client, c)
        if ent:
            await scrape_chat(client, ent, targets)

    await client.disconnect()
    print("\n[ok] done.")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--api-id", type=int, default=int(os.getenv("TELEGRAM_API_ID", 0)) or API_ID)
    p.add_argument("--api-hash", default=os.getenv("TELEGRAM_API_HASH", "") or API_HASH)
    p.add_argument("--session", default=SESSION)
    p.add_argument("--chat", action="append", help="chat to scrape (repeatable)")
    p.add_argument("--target-user", action="append", type=int, help="target user ID (repeatable)")
    p.add_argument("--export-only", action="store_true")
    p.add_argument("--export-user", action="append", type=int, help="filter export by user ID")
    p.add_argument("--output", default="my_messages.json")
    args = p.parse_args()

    init_db()
    if args.export_only:
        export(args.export_user, args.output)
        return
    if not args.api_id or not args.api_hash:
        sys.exit("[FATAL] --api-id and --api-hash required")
    asyncio.run(main_async(args))

if __name__ == "__main__":
    main()
