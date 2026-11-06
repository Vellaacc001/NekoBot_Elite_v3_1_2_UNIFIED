import re

with open('telegram_dataset_builder.py', 'r') as f:
    content = f.read()

# Replace session reference or inject constants if not present
header_patch = '''
# --- Target User & Session Configuration ---
TARGET_USER_ID = 7883544685
TARGET_USER_USERNAME = "@You_are_mine_143"
TARGET_USER_NAME = "Iziiee⋆𐙚"
SESSION_NAME = "You_are_mine_143_Iziiee_7883544685"
'''

# Update TelegramClient initialization to use SESSION_NAME if found
if 'TelegramClient(' in content:
    content = re.sub(r'TelegramClient\([^,]+', f'TelegramClient(SESSION_NAME', content)
else:
    content = header_patch + content

with open('telegram_dataset_builder.py', 'w') as f:
    f.write(content)

print("Successfully patched telegram_dataset_builder.py with target user identifiers and session name!")
