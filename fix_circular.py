filepath = "app/domain/memory/router.py"
with open(filepath, "r") as f:
    content = f.read()

content = content.replace("from app.domain.security.models import User", "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from app.domain.security.models import User\nelse:\n    User = Any")

with open(filepath, "w") as f:
    f.write(content)

print("Fixed circular import in router.py")
