from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Booking, Service, Users
from pydantic import BaseModel
from datetime import datetime
from internal_auth import verify_internal_key
import hashlib
import os

router = APIRouter(prefix="/booking", tags=["booking"])

class BookingCreate(BaseModel):
    user_id: str
    service_id: int
    booking_datetime: datetime
    special_requests: str = ""

@router.post("")
def create_booking(
    booking_in: BookingCreate, 
    db: Session = Depends(get_db), 
    _auth: bool = Depends(verify_internal_key)
):
    user_id = booking_in.user_id
    
    # Check for overlapping bookings for same service at same time
    existing = db.query(Booking).filter(
        Booking.service_id == booking_in.service_id,
        Booking.booking_datetime == booking_in.booking_datetime,
        Booking.status != 'CANCELLED'
    ).with_for_update().first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Service already booked for this time slot")
    
    service = db.query(Service).filter(Service.id == booking_in.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    booking = Booking(
        user_id=user_id,
        service_id=booking_in.service_id,
        booking_datetime=booking_in.booking_datetime,
        special_requests=booking_in.special_requests,
        amount=service.price,
        status='PENDING'
    )
    db.add(booking)
    db.flush() # Get booking.id
    
    # Prepare PayU hash
    merchant_key = os.getenv("PAYU_MERCHANT_KEY", "")
    salt = os.getenv("PAYU_MERCHANT_SALT", "")
    txnid = f"TXN_{booking.id}_{int(datetime.now().timestamp())}"
    amount = f"{service.price:.2f}"
    productinfo = service.name
    firstname = user.first_name or "Guest"
    email = user.email
    
    hash_string = f"{merchant_key}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|||||||||||{salt}"
    payment_hash = hashlib.sha512(hash_string.encode()).hexdigest()
    
    booking.payment_id = txnid
    db.commit()
    
    return {
        "booking_id": booking.id,
        "payu_payload": {
            "key": merchant_key,
            "txnid": txnid,
            "amount": amount,
            "productinfo": productinfo,
            "firstname": firstname,
            "email": email,
            "phone": "9999999999", # placeholder
            "surl": os.getenv("PAYU_SUCCESS_URL"),
            "furl": os.getenv("PAYU_FAILURE_URL"),
            "hash": payment_hash,
            "service_provider": "payu_paisa"
        }
    }

@router.get("/{id}")
def get_booking(
    id: int, 
    db: Session = Depends(get_db), 
    _auth: bool = Depends(verify_internal_key)
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    return {
        "id": booking.id,
        "user_id": booking.user_id,
        "status": booking.status,
        "amount": booking.amount,
        "datetime": booking.booking_datetime,
        "service_name": booking.service.name if booking.service else None,
        "invoice_path": booking.invoice_path
    }
