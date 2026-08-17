import os
import re

files = [
    "tests/domain/memory/test_memory_foundation.py",
    "tests/domain/memory/test_memory_operations.py",
    "tests/domain/memory/test_memory_query_intelligence.py"
]

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    # Remove the local imports added by previous scripts
    content = content.replace("    import uuid\n", "")
    content = content.replace("    from app.api.v1.auth_deps import get_current_user\n", "")
    content = content.replace("    from app.domain.security.models import User, UserRole\n", "")

    # Add them to the top of the file
    new_imports = "import uuid\nfrom app.api.v1.auth_deps import get_current_user\nfrom app.domain.security.models import User, UserRole\n"
    content = new_imports + content

    with open(filepath, "w") as f:
        f.write(content)

print("Imports restored to top of files")
