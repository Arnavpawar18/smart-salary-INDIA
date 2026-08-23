import os
import sys

mojibake_patterns = [
    'â‚¹', 'âœ', 'â€”', 'â€¢', 'â†', 'ðŸ', 'Ã', 'â€'
]

targets = ['backend/app/templates', 'backend/app/static']
found_count = 0

for target in targets:
    for root, _, files in os.walk(target):
        for f in files:
            path = os.path.join(root, f)
            try:
                with open(path, encoding='utf-8', errors='replace') as fh:
                    lines = fh.readlines()
                    for idx, line in enumerate(lines, 1):
                        for pat in mojibake_patterns:
                            if pat in line:
                                print(f"[{path}:{idx}] Found '{pat}': {line.strip()[:100]}")
                                found_count += 1
            except Exception as e:
                print(f"Error reading {path}: {e}")

print(f"\nTotal mojibake patterns detected: {found_count}")
if found_count > 0:
    sys.exit(1)
else:
    print("Encoding check: CLEAN (0 corruptions)")
