files = [
    "tests/domain/memory/test_memory_foundation.py",
    "tests/domain/memory/test_memory_operations.py",
    "tests/domain/memory/test_memory_query_intelligence.py"
]

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    content = content.replace("UserRole.ADMIN", "UserRole.admin")

    with open(filepath, "w") as f:
        f.write(content)

print("Fixed UserRole.ADMIN to UserRole.admin")
