import json
import re
import sys

def clean_text(text):
    if not text:
        return ""
    # Strip URLs
    text = re.sub(r'https?://\S+|www\.\S+', '[LINK]', text)
    # Collapse multiple whitespace/newlines
    text = re.sub(r'\n+', '\n', text).strip()
    return text

def process_raw_export(input_json, output_json, target_user_id):
    try:
        with open(input_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[Error] Input file '{input_json}' not found. Run the exporter script first.")
        return

    cleaned_pairs = []

    for entry in data:
        if entry.get('sender_id') != target_user_id:
            continue

        target_msg = clean_text(entry.get('text', ''))
        if not target_msg or len(target_msg) < 2:
            continue

        # Extract context prior to target message
        context_list = entry.get('context', [])
        prompt_parts = []
        for ctx in context_list:
            ctx_text = clean_text(ctx.get('text', ''))
            if ctx_text and ctx.get('message_id') < entry['message_id']:
                sender = ctx.get('sender_name', 'User')
                prompt_parts.append(f"{sender}: {ctx_text}")

        if not prompt_parts:
            continue

        prompt_str = "\n".join(prompt_parts)

        # Formatted for ChatML fine-tuning
        cleaned_pairs.append({
            "messages": [
                {
                    "role": "system",
                    "content": "You are simulating the speaking style, vocabulary, and persona of TargetUser."
                },
                {
                    "role": "user",
                    "content": prompt_str
                },
                {
                    "role": "assistant",
                    "content": target_msg
                }
            ]
        })

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(cleaned_pairs, f, indent=2, ensure_ascii=False)

    print(f"[Success] Processed {len(cleaned_pairs)} training conversations into '{output_json}'.")

if __name__ == "__main__":
    target_id = 7883544685  # Replace with target user ID if needed
    if len(sys.argv) > 1:
        target_id = int(sys.argv[1])
    
    process_raw_export("my_messages.json", "training_data.json", target_id)
