# app/api/v1/dev.py

from fastapi import APIRouter

router = APIRouter(prefix="/dev", tags=["Developer"])from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/dev",
    tags=["Developer"]
)

@router.post("/simulate-whatsapp")
async def simulate_whatsapp():
    return {"status": "ok"}