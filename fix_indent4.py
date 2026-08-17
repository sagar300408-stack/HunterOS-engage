filepath = "tests/domain/memory/test_memory_query_intelligence.py"
with open(filepath, 'r') as f:
    lines = f.readlines()

for i in range(508, 553):
    line = lines[i].lstrip()
    if not line:
        lines[i] = "\n"
        continue
        
    if 508 <= i <= 548:
        # Inside async with
        lines[i] = "            " + line
    elif i == 549:
        # finally
        lines[i] = "    " + line
    elif i == 550:
        # app.dependency_overrides.pop
        lines[i] = "        " + line
    elif i == 551:
        # blank
        lines[i] = "\n"
    elif i == 552:
        # blank
        lines[i] = "\n"

with open(filepath, 'w') as f:
    f.writelines(lines)
print("Indentation fixed exactly!")
