from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import lifespan
from router import (
    module1_identity,
    module2_parking,
    module3_booking,
    module4_enforcement,
    module5_ticketing
)

app = FastAPI(
    title="Smart City Traffic & Parking API",
    description="Backend API for Smart Parking and E-Challan Management System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(module1_identity.router)
app.include_router(module2_parking.router)
app.include_router(module3_booking.router)
app.include_router(module4_enforcement.router)
app.include_router(module5_ticketing.router)

@app.get("/")
async def root():
    return {"status": "online", "message": "Smart City API is running. Visit /docs for the Swagger UI."}