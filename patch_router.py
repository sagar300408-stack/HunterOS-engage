import re

filepath = "app/domain/memory/router.py"
with open(filepath, "r") as f:
    lines = f.readlines()

new_lines = []
has_injected_import = False

for i, line in enumerate(lines):
    if "from fastapi import " in line and not has_injected_import:
        new_lines.append("from app.domain.security.models import User\n")
        new_lines.append("from app.api.v1.auth_deps import get_current_user\n")
        new_lines.append(line)
        has_injected_import = True
    elif line.strip().startswith("async def ") and (line.strip().endswith("(") or "(request:" in line or "customer_id:" in line):
        new_lines.append(line)
        # inject the dependency right after `async def name(`
        if line.strip().endswith("("):
            new_lines.append("    current_user: User = Depends(get_current_user),\n")
    else:
        new_lines.append(line)

content = "".join(new_lines)
# Wait, if `async def name(request: Request` is on one line, we didn't inject!
# Let's fix that with a more robust regex on the whole string:

with open(filepath, "r") as f:
    content = f.read()

if "get_current_user" not in content:
    content = content.replace(
        "from fastapi import ",
        "from app.domain.security.models import User\nfrom app.api.v1.auth_deps import get_current_user\nfrom fastapi import "
    )

content = re.sub(r'(async def [a-zA-Z0-9_]+\()', r'\1\n    current_user: User = Depends(get_current_user),', content)

content = re.sub(r'service\.get_customer_memory\((.*?)\)', r'service.get_customer_memory(\1, workspace_id=current_user.workspace_id)', content)
content = re.sub(r'service\.get_timeline\((.*?)\)', r'service.get_timeline(\1, workspace_id=current_user.workspace_id)', content)
content = re.sub(r'service\.get_versions\((.*?)\)', r'service.get_versions(\1, workspace_id=current_user.workspace_id)', content)
content = re.sub(r'service\.get_version_by_number\((.*?)\)', r'service.get_version_by_number(\1, workspace_id=current_user.workspace_id)', content)
content = re.sub(r'service\.get_change_logs\((.*?)\)', r'service.get_change_logs(\1, workspace_id=current_user.workspace_id)', content)
content = re.sub(r'service\.get_customer_memory_history\((.*?)\)', r'service.get_customer_memory_history(\1, workspace_id=current_user.workspace_id)', content)

def inject_override(text):
    parts = re.split(r'(async def [a-zA-Z0-9_]+\(.*?\)\s*(?:->\s*[^:]+)?:\n)', text, flags=re.DOTALL)
    out = ""
    for i in range(len(parts)):
        out += parts[i]
        if i > 0 and parts[i-1].startswith("async def "):
            if "request:" in parts[i-1] or "request: " in parts[i-1]:
                out += '    if hasattr(request, "workspace_id"):\n        request.workspace_id = current_user.workspace_id\n'
    return out

content = inject_override(content)

with open(filepath, "w") as f:
    f.write(content)

print("Patched router!")
