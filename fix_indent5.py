filepath = "tests/domain/memory/test_memory_query_intelligence.py"
with open(filepath, 'r') as f:
    lines = f.readlines()

for i in range(508, len(lines)):
    line = lines[i].lstrip()
    if not line:
        lines[i] = "\n"
        continue
        
    if "finally:" in line:
        lines[i] = "    " + line
    elif "app.dependency_overrides.pop" in line:
        lines[i] = "        " + line
    else:
        # Inside async with
        lines[i] = "            " + line

with open(filepath, 'w') as f:
    f.writelines(lines)
print("Indentation fixed dynamically!")
