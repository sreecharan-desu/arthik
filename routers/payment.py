from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from database import get_db
from models import Booking
from pdfs.invoice import generate_invoice_pdf
import hashlib
import os

router = APIRouter(prefix="/payment", tags=["payment"])

@router.post("/webhook")
async def payu_webhook(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    
    # Extract data from PayU post
    status = form_data.get("status")
    txnid = form_data.get("txnid")
    amount = form_data.get("amount")
    productinfo = form_data.get("productinfo")
    firstname = form_data.get("firstname")
    email = form_data.get("email")
    posted_hash = form_data.get("hash")
    key = form_data.get("key")
    
    salt = os.getenv("PAYU_MERCHANT_SALT", "")
    
    # PayU webhook hash verification
    # reversed order hash for webhook
    # sha512(salt|status||||||udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|txnid|key)
    # assuming we don't use udf fields for now
    hash_vars_seq = [salt, status, "", "", "", "", "", "", "", "", "", email, firstname, productinfo, amount, txnid, key]
    hash_string = "|".join(hash_vars_seq)
    
    calculated_hash = hashlib.sha512(hash_string.encode()).hexdigest()
    
    if calculated_hash != posted_hash:
        return Response(content="Invalid Signature", status_code=403)
    
    if status == "success":
        booking = db.query(Booking).filter(Booking.payment_id == txnid).first()
        if booking:
            booking.status = "CONFIRMED"
            
            # Generate invoice
            pdf_path = os.path.join(os.getenv("PDF_TEMP_PATH", "/tmp"), f"invoice_{booking.id}.pdf")
            generate_invoice_pdf(booking, pdf_path)
            booking.invoice_path = pdf_path
            
            db.commit()
    
    return {"status": "ok"}

@router.get("/success")
def payment_success():
    return {"message": "Payment successful. Your booking is confirmed."}

@router.get("/fail")
def payment_fail():
    return {"message": "Payment failed. Please try again."}
