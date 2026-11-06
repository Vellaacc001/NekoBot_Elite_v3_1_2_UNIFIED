import asyncio
import json
import os
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

HOME = os.path.expanduser("~")
SESSION_NAME = os.path.join(HOME, "nanora_session")
TARGET_CHAT_ID = -1003909898828
NANORA_USER_ID = 6883478130

QUESTIONS_FILE = os.path.join(HOME, "nanora_dataset", "questions.txt")
DATASET_FILE = os.path.join(HOME, "nanora_dataset", "nanora_dataset.jsonl")

RESPONSE_TIMEOUT = 60
DELAY_BETWEEN_QUESTIONS = 8

API_ID = 37165294
API_HASH = "49dc7b3bfdf9ed434bcebc205595e27b"

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
                if record.get("status") == "completed":
                    completed.add(record.get("question_id"))
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

async def main():
    questions = load_questions()
    completed = load_completed()

    print("\n======================================")
    print(" NANORA JSONL COLLECTOR (EVENT-DRIVEN)")
    print("======================================")
    print(f"Questions loaded : {len(questions)}")
    print(f"Already completed: {len(completed)}\n")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"Logged in as: {getattr(me, 'first_name', 'Unknown')}\n")

    try:
        for question_id, question in enumerate(questions, 1):
            if question_id in completed:
                print(f"[{question_id}/{len(questions)}] SKIP - already completed")
                continue

            print("=" * 60)
            print(f"Q{question_id}/{len(questions)}: {question}")

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

            print(f"Sent message ID: {sent.id}")

            try:
                await asyncio.wait_for(response_event.wait(), timeout=RESPONSE_TIMEOUT)
            except asyncio.TimeoutError:
                print(f"TIMEOUT - no Nanora response for Q{question_id}")
                client.remove_event_handler(handler)
                await asyncio.sleep(DELAY_BETWEEN_QUESTIONS)
                continue

            client.remove_event_handler(handler)

            responses.sort(key=lambda m: m.id)
            response_texts = [msg.text for msg in responses if msg.text]
            combined_response = "\n".join(response_texts)
            first_response = responses[0]

            is_reply = False
            if first_response.reply_to:
                try:
                    is_reply = (first_response.reply_to.reply_to_msg_id == sent.id)
                except Exception:
                    pass

            record = {
                "question_id": question_id,
                "category": "General",
                "question": question,
                "sent_message": message_text,
                "question_msg_id": sent.id,
                "sent_timestamp": sent_timestamp,
                "nanora_response": combined_response,
                "nanora_msg_ids": [msg.id for msg in responses],
                "received_timestamp": (
                    first_response.date.isoformat()
                    if first_response.date
                    else now_iso()
                ),
                "response_message_count": len(responses),
                "is_reply": is_reply,
                "sender_id": NANORA_USER_ID,
                "status": "completed"
            }

            save_record(record)
            print("\nNANORA:")
            print(combined_response)
            print(f"\n✓ Q{question_id} saved\n")

            await asyncio.sleep(DELAY_BETWEEN_QUESTIONS)

    except KeyboardInterrupt:
        print("\nStopped by user. Progress saved.")
    finally:
        await client.disconnect()
        print("Collector finished.")

if __name__ == "__main__":
    asyncio.run(main())
