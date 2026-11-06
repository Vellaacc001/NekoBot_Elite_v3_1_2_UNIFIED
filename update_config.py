import re

with open('telegram_dataset_builder.py', 'r') as f:
    code = f.read()

# Replace session name if hardcoded, or ensure session uses our new filename variable
# Let's inject our explicit target constants
constants_patch = '''
# --- Target User Definition (Immutable ID + Handles) ---
TARGET_USER_ID = 7883544685
TARGET_USER_USERNAME = "@You_are_mine_143"
TARGET_USER_NAME = "Iziiee⋆𐙚"
SESSION_NAME = "You_are_mine_143_Iziiee_7883544685"
-------------------------------------------------------
'''

print("Configuration definitions prepared.")
