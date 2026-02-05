from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Bella Italia Voice Service", version="1.0.0")

# Import and include routers
from .api.tables import router as tables_router
app.include_router(tables_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:3001")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")

# Health check endpoints
@app.get("/health/live")
async def liveness():
    return {
        "status": "ok",
        "service": "voice",
        "version": "1.0.0"
    }

@app.get("/health/ready")
async def readiness():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/health/live", timeout=2.0)
            backend_ok = response.status_code == 200
        
        return {
            "status": "ready" if backend_ok else "not ready",
            "service": "voice",
            "dependencies": {
                "backend": "connected" if backend_ok else "disconnected",
                "elevenlabs": "configured" if ELEVENLABS_API_KEY else "not configured"
            }
        }
    except Exception as e:
        return {
            "status": "not ready",
            "error": str(e)
        }

# Request models
class ReservationRequest(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    party_size: int
    reservation_date: str
    reservation_time: str
    special_requests: Optional[str] = None

class MenuQueryRequest(BaseModel):
    query: str
    category: Optional[str] = None

# Endpoints
@app.post("/api/reservations")
async def create_reservation(reservation: ReservationRequest):
    """Create a reservation via voice"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/api/reservations",
                json={
                    **reservation.dict(),
                    "source": "voice"
                },
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Backend error: {str(e)}")

@app.post("/api/check-availability")
async def check_availability(date: str, time: str, party_size: int):
    """Check table availability"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/api/reservations/check-availability",
                json={"date": date, "time": time, "party_size": party_size},
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Backend error: {str(e)}")

@app.get("/api/menu")
async def get_menu():
    """Get full menu"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/api/menu", timeout=5.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Backend error: {str(e)}")

@app.get("/api/menu/category/{category}")
async def get_menu_by_category(category: str):
    """Get menu items by category"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/menu/category/{category}",
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Backend error: {str(e)}")

@app.get("/")
async def root():
    return {
        "service": "Bella Italia Voice Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health/live",
            "readiness": "/health/ready",
            "reservations": "/api/reservations",
            "menu": "/api/menu",
            "tables": "/widget-api/tables/v1/"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
