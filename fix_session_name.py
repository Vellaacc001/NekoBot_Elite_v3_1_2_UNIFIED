with open('telegram_dataset_builder.py', 'r') as f:
    lines = f.readlines()

# Filter out any old broken definitions if they exist
new_lines = []
skip = False
for line in lines:
    if "--- Target User & Session Configuration ---" in line:
        skip = True
    if skip and "---" in line and len(line.strip()) > 5:
        skip = False
        continue
    if not skip:
        new_lines.append(line)

# Prepend correct configuration definitions at the very top
header_config = '''# --- Target User & Session Configuration ---
TARGET_USER_ID = 7883544685
TARGET_USER_USERNAME = "@You_are_mine_143"
TARGET_USER_NAME = "Iziiee⋆𐙚"
SESSION_NAME = "You_are_mine_143_Iziiee_7883544685"
# ---------------------------------------------

'''

code = header_config + "".join(new_lines)

with open('telegram_dataset_builder.py', 'w') as f:
    f.write(code)

print("Successfully injected SESSION_NAME and target user details into telegram_dataset_builder.py!")
