import asyncio
from app.main import create_app
import uuid
from app.api.v1.auth_deps import get_current_user
from app.domain.security.models import User, UserRole

def test():
    app = create_app()
    print("App created")
    print("get_current_user is", get_current_user)

test()
