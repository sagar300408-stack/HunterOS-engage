filepath = "tests/domain/memory/test_memory_query_intelligence.py"
with open(filepath, 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # From line 509 to the end of the try block, decrease indentation by 4 spaces
    # Wait, the try block ends around line 560 where finally block is
    if 508 <= i <= 580:
        if line.startswith("            "):
            # If it starts with 12 spaces, replace first 4
            new_lines.append(line[4:])
        elif line.startswith("        "):
            new_lines.append(line[4:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(filepath, 'w') as f:
    f.writelines(new_lines)
print("Indentation fixed for the rest of the function")
