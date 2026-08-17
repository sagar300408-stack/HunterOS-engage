import re
import uuid

def patch_test_file(filepath, setup_pattern, replace_pattern):
    with open(filepath, 'r') as f:
        content = f.read()

    if "get_current_user" not in content:
        imports = "from app.api.v1.auth_deps import get_current_user\nfrom app.domain.security.models import User, UserRole\nimport uuid"
        content = content.replace("from app.integrations.postgres.database import get_db", f"from app.integrations.postgres.database import get_db\n{imports}")

    content = re.sub(setup_pattern, replace_pattern, content, flags=re.DOTALL)
    
    with open(filepath, 'w') as f:
        f.write(content)

# File 1: test_memory_foundation.py
f1 = "tests/domain/memory/test_memory_foundation.py"
setup1 = r'(customer_id = uuid\.uuid4\(\)\n\s*customer = Customer\(id=customer_id, phone="\+919777788888", name="API Test Customer"\)\n\s*async_session\.add\(customer\)\n\s*await async_session\.commit\(\)\n\s*app = create_app\(\)\n\s*# Override get_db dependency to use our isolated test async_session\n\s*async def override_get_db\(\):\n\s*yield async_session\n\s*app\.dependency_overrides\[get_db\] = override_get_db)'

rep1 = """        workspace_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer = Customer(id=customer_id, phone="+919777788888", name="API Test Customer", workspace_id=workspace_id)
        async_session.add(customer)
        await async_session.commit()
    
        app = create_app()
    
        # Override get_db dependency to use our isolated test async_session
        async def override_get_db():
            yield async_session
            
        async def override_get_current_user():
            return User(id=uuid.uuid4(), email="test@test.com", workspace_id=workspace_id, role=UserRole.ADMIN)
    
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user"""

patch_test_file(f1, setup1, rep1)


# File 2: test_memory_operations.py
f2 = "tests/domain/memory/test_memory_operations.py"
setup2 = r'(async def override_get_db\(\):\n\s*yield async_session\n\s*app\.dependency_overrides\[get_db\] = override_get_db\n\s*transport = ASGITransport\(app=app\)\n\s*async with AsyncClient\(transport=transport, base_url="http://test"\) as client:\n\s*customer_id = uuid4\(\)\n\s*customer = Customer\(id=customer_id, phone="\+919876543299", name="REST API User"\))'

rep2 = """        workspace_id = uuid.uuid4()
        async def override_get_db():
            yield async_session
            
        async def override_get_current_user():
            return User(id=uuid.uuid4(), email="test@test.com", workspace_id=workspace_id, role=UserRole.ADMIN)
    
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
    
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer_id = uuid.uuid4()
            customer = Customer(id=customer_id, phone="+919876543299", name="REST API User", workspace_id=workspace_id)"""

patch_test_file(f2, setup2, rep2)

# File 3: test_memory_query_intelligence.py
f3 = "tests/domain/memory/test_memory_query_intelligence.py"
setup3 = r'(async def override_get_db\(\):\n\s*yield db_session\n\s*app\.dependency_overrides\[get_db\] = override_get_db\n\s*try:\n\s*transport = ASGITransport\(app=app\)\n\s*async with AsyncClient\(transport=transport, base_url="http://test"\) as client:\n\s*target_rec = seed_data\["records"\]\[0\]\n\s*cid = str\(target_rec\.customer_id\)\n\s*wid = str\(seed_data\["workspace_a"\]\))'

rep3 = """        async def override_get_db():
            yield db_session
            
        async def override_get_current_user():
            return User(id=uuid.uuid4(), email="test@test.com", workspace_id=seed_data["workspace_a"], role=UserRole.ADMIN)
    
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                target_rec = seed_data["records"][0]
                cid = str(target_rec.customer_id)
                wid = str(seed_data["workspace_a"])"""

patch_test_file(f3, setup3, rep3)

print("Patch applied to all 3 test files.")
