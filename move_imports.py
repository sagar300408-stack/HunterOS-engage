import os

files = [
    "tests/domain/memory/test_memory_foundation.py",
    "tests/domain/memory/test_memory_operations.py",
    "tests/domain/memory/test_memory_query_intelligence.py"
]

import_lines = [
    "import uuid\n",
    "from app.api.v1.auth_deps import get_current_user\n",
    "from app.domain.security.models import User, UserRole\n"
]

for filepath in files:
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Remove the imports from the top
    new_lines = []
    for line in lines:
        if any(imp.strip() in line for imp in import_lines):
            continue
        new_lines.append(line)
        
    # Inject them inside the test functions right after the docstring
    final_lines = []
    in_test = False
    for line in new_lines:
        final_lines.append(line)
        if "def test_rest_api_endpoints_integration" in line or \
           "def test_rest_api_lifecycle_and_concurrency_endpoints" in line or \
           "def test_rest_api_query_endpoints" in line:
            in_test = True
        elif in_test and '"""' in line:
            # We found the docstring end
            in_test = False
            # Insert imports here
            final_lines.append("    import uuid\n")
            final_lines.append("    from app.api.v1.auth_deps import get_current_user\n")
            final_lines.append("    from app.domain.security.models import User, UserRole\n")

    with open(filepath, 'w') as f:
        f.writelines(final_lines)
    print(f"Moved imports in {filepath}")
