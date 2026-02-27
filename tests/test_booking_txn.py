import pytest
from fastapi.testclient import TestClient
from main import app
from database import get_db, Base, engine
from sqlalchemy.orm import sessionmaker
import models
from datetime import datetime

# Setup test DB
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:

        # Reset autoincrement counters
        db.execute("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));")
        db.execute("SELECT setval('services_id_seq', (SELECT MAX(id) FROM services));")
        db.execute("SELECT setval('bookings_id_seq', (SELECT MAX(id) FROM bookings));")
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_double_booking():
    # Setup: Create a user and a service
    db = TestingSessionLocal()
    user = models.User(email="test@example.com", username="testuser", hashed_password="pw", role="guest")
    db.add(user)
    db.flush()
    
    provider = models.LocalProvider(name="Test Prov", city="Test City")
    db.add(provider)
    db.flush()
    
    service = models.Service(provider_id=provider.id, name="Test Svc", type="TOUR", price=100.0, is_available=True)
    db.add(service)
    db.commit()
    
    booking_data = {
        "user_id": user.id,
        "service_id": service.id,
        "booking_datetime": "2026-05-12T10:00:00",
        "special_requests": "None"
    }
    
    # First booking
    resp1 = client.post("/booking", json=booking_data)
    assert resp1.status_code == 200
    
    # Second booking same time (should fail)
    resp2 = client.post("/booking", json=booking_data)
    assert resp2.status_code == 400
    assert "already booked" in resp2.json()["detail"]
