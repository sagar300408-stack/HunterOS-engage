import os

files = [
    "tests/domain/memory/test_memory_foundation.py",
    "tests/domain/memory/test_memory_operations.py",
    "tests/domain/memory/test_memory_query_intelligence.py"
]

imports = """
import uuid
from app.api.v1.auth_deps import get_current_user
from app.domain.security.models import User, UserRole
"""

for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()
    
    if "from app.api.v1.auth_deps import get_current_user" not in content:
        with open(filepath, 'w') as f:
            f.write(imports + content)
            print(f"Added imports to {filepath}")
