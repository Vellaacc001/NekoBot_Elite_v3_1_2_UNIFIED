import re
import sys

INPUT_FILE = "questions_raw.txt"
OUTPUT_FILE = "questions.txt"

questions = []

# Regex patterns to catch various question formatting styles
p1 = re.compile(r"^\s*(\d+)[\.\)]\s*(.+)$", re.DOTALL)
p2 = re.compile(r"^\s*Question\s+(?:no\.?|num\.?|number)?\s*(\d+)\s*[\:\-]\s*(.+)$", re.IGNORECASE | re.DOTALL)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line_num, line in enumerate(f, 1):
        clean_line = line.strip()
        if not clean_line:
            continue
        
        m = p2.match(clean_line) or p1.match(clean_line)
        if m:
            q_num = int(m.group(1))
            q_text = m.group(2).strip()
            questions.append((q_num, q_text))
        else:
            print(f"[WARNING] Could not parse line {line_num}: {clean_line[:50]}...")

# Sort strictly by question index
questions.sort(key=lambda x: x[0])

# Validate dataset integrity
extracted_numbers = [n for n, _ in questions]
expected_numbers = list(range(1, 1094))

missing = set(expected_numbers) - set(extracted_numbers)
extra = set(extracted_numbers) - set(expected_numbers)

print("=" * 50)
print("QUESTION PREPARATION REPORT")
print("=" * 50)
print(f"Total Parsed     : {len(questions)}")
print(f"Expected Count   : 1093")
print(f"Missing Indices  : {len(missing)} -> {sorted(list(missing))[:10] if missing else 'None'}")
print(f"Extra Indices    : {len(extra)} -> {sorted(list(extra))[:10] if extra else 'None'}")

if len(questions) == 1093 and not missing and not extra:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for _, q_text in questions:
            # Flatten internal linebreaks to ensure 1 line per question
            single_line_q = " ".join(q_text.splitlines())
            f.write(single_line_q + "\n")
    print("\n✓ SUCCESS: Exactly 1093 questions written to questions.txt")
else:
    print("\n⚠ FAILURE: Dataset extraction misaligned. Review questions_raw.txt before running collector.")
    sys.exit(1)
