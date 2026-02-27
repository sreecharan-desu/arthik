from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routers import auth, hotels, booking, payment, vendor, chat, users
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
app.include_router(chat.router)
app.include_router(users.router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)