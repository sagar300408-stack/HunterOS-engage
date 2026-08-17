import re

def fix_indentation(filepath, old, new):
    with open(filepath, 'r') as f:
        content = f.read()
    
    content = content.replace(old, new)
    
    with open(filepath, 'w') as f:
        f.write(content)

# File 1
f1 = "tests/domain/memory/test_memory_foundation.py"
old1 = """    \"\"\"Test REST API routes using FastAPI test client.\"\"\"
            workspace_id = uuid.uuid4()
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

new1 = """    \"\"\"Test REST API routes using FastAPI test client.\"\"\"
    workspace_id = uuid.uuid4()
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

fix_indentation(f1, old1, new1)


# File 2
f2 = "tests/domain/memory/test_memory_operations.py"
old2 = """    app = create_app()

            workspace_id = uuid.uuid4()
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

new2 = """    app = create_app()

    workspace_id = uuid.uuid4()
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

fix_indentation(f2, old2, new2)


# File 3
f3 = "tests/domain/memory/test_memory_query_intelligence.py"
old3 = """    \"\"\"Verify REST API query routes for projections, cursor search, stats, and export.\"\"\"
        async def override_get_db():
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

new3 = """    \"\"\"Verify REST API query routes for projections, cursor search, stats, and export.\"\"\"
    async def override_get_db():
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

fix_indentation(f3, old3, new3)

print("Fixed indentation")
