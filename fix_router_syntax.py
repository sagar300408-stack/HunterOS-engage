import re

filepath = "app/domain/memory/router.py"
with open(filepath, "r") as f:
    content = f.read()

# 1. Remove the faulty injection
content = re.sub(r'(async def [a-zA-Z0-9_]+\(\n)\s*current_user: User = Depends\(get_current_user\),\n', r'\1', content)

# 2. Inject right before db: AsyncSession
content = content.replace(
    'db: AsyncSession = Depends(get_db),',
    'current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),'
)

with open(filepath, "w") as f:
    f.write(content)

print("Fixed router syntax!")
