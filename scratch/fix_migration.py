import re

filepath = 'alembic/versions/c6a81410ce8e_add_missing_columns_and_sync_schema.py'
with open(filepath, 'r') as f:
    content = f.read()

# Replace op.drop_table('tablename') with op.execute('DROP TABLE IF EXISTS tablename CASCADE')
content = re.sub(
    r"op\.drop_table\('([^']+)'\)", 
    r"op.execute('DROP TABLE IF EXISTS \1 CASCADE')", 
    content
)

with open(filepath, 'w') as f:
    f.write(content)

print("Migration file updated.")
