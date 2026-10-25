target = 'if os.environ.get("WHATSAPP_TEST_AUTO_REPLY", "").lower() == "true":'
replacement = 'if os.environ.get("ENABLE_WHATSAPP_TEST_AUTO_REPLY", "").lower() == "true":'

with open('app/pipeline/ai.py', 'r', encoding='utf-8') as f:
    content = f.read()

assert target in content, "Target string not found in app/pipeline/ai.py"
updated = content.replace(target, replacement, 1)

with open('app/pipeline/ai.py', 'w', encoding='utf-8', newline='') as f:
    f.write(updated)

print("Updated app/pipeline/ai.py successfully.")
