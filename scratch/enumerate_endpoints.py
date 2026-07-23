import sys
import json
import logging
import asyncio
from fastapi.routing import APIRoute, APIWebSocketRoute

import os
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/hunteros"
os.environ["OPENAI_API_KEY"] = "test"
os.environ["WHATSAPP_ACCESS_TOKEN"] = "test"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "test"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test"
os.environ["APP_ENV"] = "testing"

import app.main

def get_routes():
    try:
        application = app.main.create_app()
        routes = []
        for route in application.routes:
            if isinstance(route, APIRoute):
                routes.append({
                    "path": route.path,
                    "name": route.name,
                    "methods": list(route.methods)
                })
            elif isinstance(route, APIWebSocketRoute):
                routes.append({
                    "path": route.path,
                    "name": route.name,
                    "methods": ["WS"]
                })
        print(json.dumps(routes, indent=2))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_routes()
