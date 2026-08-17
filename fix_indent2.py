import re

filepath = "tests/domain/memory/test_memory_query_intelligence.py"
with open(filepath, 'r') as f:
    content = f.read()

# I will find the exact test definition and replace it safely
pattern = r'@pytest\.mark\.asyncio\nasync def test_rest_api_query_endpoints\(async_engine, db_session, seed_data\):\n    """Verify REST API query routes for projections, cursor search, stats, and export."""(.*?)(?=\n            async with AsyncClient\(transport=transport, base_url="http://test"\) as client:)'

new_setup = """
    async def override_get_db():
        yield db_session
        
    async def override_get_current_user():
        return User(id=uuid.uuid4(), email="test@test.com", workspace_id=seed_data["workspace_a"], role=UserRole.ADMIN)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        transport = ASGITransport(app=app)"""

content = re.sub(pattern, f'@pytest.mark.asyncio\nasync def test_rest_api_query_endpoints(async_engine, db_session, seed_data):\n    """Verify REST API query routes for projections, cursor search, stats, and export."""{new_setup}', content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)

print("Fixed!")
