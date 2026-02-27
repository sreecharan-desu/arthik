from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Booking
from pdfs.invoice import generate_invoice_pdf
import hashlib
import os
import urllib.parse

router = APIRouter(prefix="/payment", tags=["payment"])

def verify_payu_hash(form_data: dict, salt: str) -> bool:
    status = form_data.get("status", "")
    txnid = form_data.get("txnid", "")
    amount = form_data.get("amount", "")
    productinfo = form_data.get("productinfo", "")
    firstname = form_data.get("firstname", "")
    email = form_data.get("email", "")
    posted_hash = form_data.get("hash", "")
    key = form_data.get("key", "")
    udf1 = form_data.get("udf1", "")
    
    # PayU webhook hash verification
    # reversed order hash for webhook/success response
    hash_vars_seq = [salt, status, "", "", "", "", "", "", "", "", "", udf1, email, firstname, productinfo, amount, txnid, key]
    hash_string = "|".join(hash_vars_seq)
    
    calculated_hash = hashlib.sha512(hash_string.encode()).hexdigest()
    return calculated_hash == posted_hash

@router.post("/callback/success")
async def payu_success_callback(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    form_dict = dict(form_data)
    
    txnid = form_dict.get("txnid", "unknown")
    status = form_dict.get("status")
    
    print(f"PayU Success Callback received for TXN: {txnid}")
    
    salt = os.getenv("PAYU_MERCHANT_SALT", "")
    is_valid = verify_payu_hash(form_dict, salt)
    
    frontend_base = os.getenv("FRONTEND_URL", "http://localhost:5173")
    frontend_success_url = f"{frontend_base}/payment/success"
    frontend_failure_url = f"{frontend_base}/payment/failure"
    
    redirect_url = f"{frontend_failure_url}?txnid={txnid}&error=verification_failed"
    
    try:
        if is_valid and status == "success":
            booking_id = form_dict.get("udf1")
            
            if booking_id:
                try:
                    booking_id_int = int(booking_id)
                    booking = db.query(Booking).filter(Booking.id == booking_id_int).first()
                    
                    if booking:
                        booking.status = "CONFIRMED"
                        try:
                            pdf_path = os.path.join(os.getenv("PDF_TEMP_PATH", "/tmp"), f"invoice_{booking.id}.pdf")
                            generate_invoice_pdf(booking, pdf_path)
                            booking.invoice_path = pdf_path
                        except Exception as e:
                            print(f"Failed to generate invoice for {booking_id}: {e}")
                        db.commit()
                        print(f"Booking {booking_id} marked as CONFIRMED.")
                    else:
                        print(f"Booking {booking_id} not found in DB. Maybe mock booking.")
                    
                    redirect_url = f"{frontend_success_url}?txnid={txnid}"
                except ValueError:
                    print(f"Invalid booking ID format: {booking_id}")
                    redirect_url = f"{frontend_failure_url}?txnid={txnid}&error=invalid_order_id"
            else:
                print("Order ID (udf1) missing in PayU response")
                redirect_url = f"{frontend_failure_url}?txnid={txnid}&error=missing_order_id"
        else:
            print(f"PayU Hash Verification failed. Hash valid: {is_valid}, Status: {status}")
            redirect_url = f"{frontend_failure_url}?txnid={txnid}&error=hash_mismatch"
    except Exception as e:
        print(f"Critical error in payment success callback: {e}")
        redirect_url = f"{frontend_failure_url}?error=internal_callback_error"
        
    print(f"Redirecting user to: {redirect_url}")
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/callback/failure")
async def payu_failure_callback(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    form_dict = dict(form_data)
    
    txnid = form_dict.get("txnid", "unknown")
    print(f"PayU Failure Callback received for TXN: {txnid}")
    
    try:
        booking_id = form_dict.get("udf1")
        if booking_id:
            try:
                booking_id_int = int(booking_id)
                booking = db.query(Booking).filter(Booking.id == booking_id_int).first()
                if booking:
                    booking.status = "FAILED"
                    db.commit()
                    print(f"Booking {booking_id} marked as FAILED in database.")
            except ValueError:
                pass
    except Exception as e:
        print(f"Database update failed for failed transaction {txnid}: {e}")
        
    frontend_base = os.getenv("FRONTEND_URL", "http://localhost:5173")
    frontend_failure_url = f"{frontend_base}/payment/failure"
    
    error_msg = form_dict.get("error_Message") or form_dict.get("field9") or "Payment Failed"
    error_params = urllib.parse.urlencode({'txnid': txnid, 'error': error_msg})
    
    final_redirect = f"{frontend_failure_url}?{error_params}"
    
    print(f"Redirecting user to failure page: {final_redirect}")
    return RedirectResponse(url=final_redirect, status_code=303)
