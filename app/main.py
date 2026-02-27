from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.models import models
from app.db.session import engine
from app.api.v1.endpoints import auth, hotels, booking, payment, vendor, users, agent
import os

app = FastAPI(title="Concierge Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models creation (fallback if not using migrations)
# models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(hotels.router)
app.include_router(booking.router)
app.include_router(payment.router)
app.include_router(vendor.router)
app.include_router(users.router)
app.include_router(agent.router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

