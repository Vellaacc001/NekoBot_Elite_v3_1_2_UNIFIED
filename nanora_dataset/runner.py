import asyncio
import json
import os
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# CONFIGURATION
HOME = os.path.expanduser("~")
SESSION_NAME = os.path.join(HOME, "nanora_session")
TARGET_CHAT_ID = -1003909898828
NANORA_USER_ID = 6883478130

QUESTIONS_FILE = os.path.join(HOME, "nanora_dataset", "questions.txt")
DATASET_FILE = os.path.join(HOME, "nanora_dataset", "nanora_dataset.jsonl")

RESPONSE_TIMEOUT = 60
DELAY_BETWEEN_QUESTIONS = 10
BATCH_LIMIT = 85

API_ID = 37165294
API_HASH = "49dc7b3bfdf9ed434bcebc205595e27b"

# UTILITIES
def now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_completed():
    completed = set()
    if not os.path.exists(DATASET_FILE):
        return completed
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                qid = record.get("question_id")
                if qid is not None:
                    completed.add(qid)
            except json.JSONDecodeError:
                pass
    return completed

def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def save_record(record):
    with open(DATASET_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())

def get_category(q_id):
    if 1 <= q_id <= 25: return "Identity / Personality"
    if 26 <= q_id <= 60: return "Humor / Sarcasm"
    if 61 <= q_id <= 80: return "Casual Conversation"
    if 81 <= q_id <= 105: return "Emotional Support / Motivation"
    if 106 <= q_id <= 150: return "Philosophy / Psychology / Relationships"
    if 151 <= q_id <= 175: return "Anime / Pop Culture"
    if 176 <= q_id <= 250: return "Programming / Technical"
    if 251 <= q_id <= 275: return "Nanora Personality Architecture"
    return "General"

async def main():
    questions = load_questions()
    completed = load_completed()

    print("\n==================================================")
    print("NANORA JSONL COLLECTOR (EVENT-DRIVEN)")
    print("==================================================")
    print(f"Questions loaded : {len(questions)}")
    print(f"Already completed: {len(completed)}\n")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"Logged in as: {getattr(me, 'first_name', 'Unknown')}\n")

    batch_count = 0

    try:
        for question_id, question in enumerate(questions, 1):
            if question_id in completed:
                continue

            if batch_count >= BATCH_LIMIT:
                print(f"\n[!] Reached batch limit of {BATCH_LIMIT} questions. Stopping session automatically.")
                break

            print("=" * 60)
            print(f"Q{question_id}/{len(questions)} | Category: {get_category(question_id)}")
            print(f"Question: {question}")

            message_text = f"@nanorabot {question}"
            sent_timestamp = now_iso()

            responses = []
            response_event = asyncio.Event()

            @client.on(events.NewMessage(chats=TARGET_CHAT_ID, from_users=NANORA_USER_ID))
            async def handler(event):
                responses.append(event.message)
                await asyncio.sleep(3)
                response_event.set()

            try:
                sent = await client.send_message(TARGET_CHAT_ID, message_text)
            except FloodWaitError as e:
                print(f"Telegram requested a {e.seconds}s wait.")
                await asyncio.sleep(e.seconds)
                sent = await client.send_message(TARGET_CHAT_ID, message_text)

            print(f"Sent Message ID: {sent.id}")

            try:
                await asyncio.wait_for(response_event.wait(), timeout=RESPONSE_TIMEOUT)
            except asyncio.TimeoutError:
                print(f"TIMEOUT - no Nanora response for Q{question_id}")
                client.remove_event_handler(handler)
                await asyncio.sleep(DELAY_BETWEEN_QUESTIONS)
                continue

            client.remove_event_handler(handler)

            full_reply_text = "\n\n".join([m.text for m in responses if m.text])
            first_msg = responses[0]

            record = {
                "question_id": question_id,
                "category": get_category(question_id),
                "question": question,
                "nanora_response": full_reply_text,
                "sent_timestamp": sent_timestamp,
                "received_timestamp": now_iso(),
                "sent_message_id": sent.id,
                "received_message_id": first_msg.id,
                "chat_id": TARGET_CHAT_ID,
                "status": "completed"
            }

            save_record(record)
            batch_count += 1
            print(f"\nNANORA:\n{full_reply_text}\n")
            print(f"✓ Q{question_id} saved (Batch progress: {batch_count}/{BATCH_LIMIT})\n")

            await asyncio.sleep(DELAY_BETWEEN_QUESTIONS)

    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
