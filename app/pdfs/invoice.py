from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def generate_invoice_pdf(booking, output_path):
    """
    Generates a PDF invoice for the given booking.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 100, "CONCIERGE BOOKING INVOICE")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 130, f"Invoice ID: INV-{booking.id}")
    c.drawString(100, height - 150, f"Booking ID: {booking.id}")
    c.drawString(100, height - 170, f"Date: {booking.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    c.drawString(100, height - 210, f"Guest: {booking.user.first_name} {booking.user.last_name}")
    c.drawString(100, height - 230, f"Service: {booking.service.name}")
    c.drawString(100, height - 250, f"Scheduled Time: {booking.booking_datetime.strftime('%Y-%m-%d %H:%M')}")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, height - 290, "Payment Details:")
    c.setFont("Helvetica", 12)
    c.drawString(120, height - 310, f"Amount: {booking.amount:.2f} INR")
    c.drawString(120, height - 330, f"Status: {booking.status}")
    c.drawString(120, height - 350, f"Transaction ID: {booking.payment_id}")
    
    c.drawString(100, height - 400, "Tax Breakdown (Dummy):")
    gst = booking.amount * 0.18
    c.drawString(120, height - 420, f"Base Price: {booking.amount - gst:.2f}")
    c.drawString(120, height - 440, f"GST (18%): {gst:.2f}")
    c.drawString(120, height - 460, f"Total: {booking.amount:.2f}")
    
    c.drawString(100, 100, "System Generated Invoice - No signature required.")
    
    c.showPage()
    c.save()
    return output_path
