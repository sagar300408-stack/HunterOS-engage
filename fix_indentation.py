import re

filepath = "app/domain/memory/router.py"
with open(filepath, "r") as f:
    content = f.read()

content = content.replace('    if hasattr(request, "workspace_id"):\n        request.workspace_id = current_user.workspace_id\n', '')

def inject_override(text):
    parts = re.split(r'(async def [a-zA-Z0-9_]+\(.*?\)\s*(?:->\s*[^:]+)?:\n)', text, flags=re.DOTALL)
    out = ""
    for i in range(len(parts)):
        if i % 2 == 1:
            out += parts[i]
        else:
            body = parts[i]
            if i > 0 and ("request:" in parts[i-1] or "request: " in parts[i-1]):
                body = '    if hasattr(request, "workspace_id"):\n        request.workspace_id = current_user.workspace_id\n' + body
            out += body
    return out

content = inject_override(content)

with open(filepath, "w") as f:
    f.write(content)

print("Fixed indentation!")
