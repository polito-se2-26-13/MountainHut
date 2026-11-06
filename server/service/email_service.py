"""Email Template & Formatting Service (MH-03: Receive Confirmation)."""
from typing import Dict, Any, Optional
from server.models.DAO.reservation import ReservationDAO
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from server.models.DTO.reservation_dto import ReservationMailDTO
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH, override=True)

def format_booking_email_text(reservation: ReservationMailDTO) -> str:
    """
    Generate plain text confirmation email for a reservation (MH-03).
    Includes:
    - booking reference
    - date and time slot
    - party size
    - possible party requirements (allergies)
    - name of the hiker who made the reservation
    """
    """
    conf = reservation.to_confirmation_dict()
    hiker_name = conf.get("hikerName") or "Valued Guest"
    ref = conf.get("bookingReference") or "N/A"
    date_str = conf.get("date") or "N/A"
    time_slot = conf.get("timeSlot") or "N/A"
    party_size = conf.get("partySize") or 1
    special_reqs = conf.get("specialRequirements") or "None specified"
    tables = conf.get("assignedTables") or []
"""
    hiker_name=reservation.hiker_name
    ref= reservation.booking_reference
    date_str = reservation.date_str
    time_slot = reservation.time_slot
    party_size = reservation.party_size
    special_reqs = reservation.special_reqs or "None specified"
    text = f"""============================================================
           MOUNTAIN HUT - RESERVATION CONFIRMATION
============================================================

Dear {hiker_name},

Thank you for booking with Mountain Hut! Your reservation is confirmed.

------------------------------------------------------------
BOOKING DETAILS (Reference: {ref})
------------------------------------------------------------
* Hiker Name:          {hiker_name}
* Booking Reference:   {ref}
* Date:                {date_str}
* Time Slot:           {time_slot}
* Party Size:          {party_size} person(s)
* Special Requests:    {special_reqs}

We look forward to welcoming you to the hut!

Warm regards,
The Mountain Hut Team
============================================================
"""
    return text.strip()


def format_booking_email_html(reservation: ReservationMailDTO) -> str:
    """
    Generate a clean, responsive HTML email template for booking confirmation (MH-03).
    """
    '''conf = reservation.to_confirmation_dict()
    hiker_name = conf.get("hikerName") or "Valued Guest"
    ref = conf.get("bookingReference") or "N/A"
    date_str = conf.get("date") or "N/A"
    time_slot = conf.get("timeSlot") or "N/A"
    party_size = conf.get("partySize") or 1
    special_reqs = conf.get("specialRequirements") or "None specified"
    tables = conf.get("assignedTables") or []'''
    hiker_name=reservation.hiker_name
    ref= reservation.booking_reference
    date_str = reservation.date_str
    time_slot = reservation.time_slot
    party_size = reservation.party_size
    special_reqs = reservation.special_reqs or "None specified"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Mountain Hut Booking Confirmation</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    
    <!-- Header -->
    <div style="background-color: #0f172a; color: #ffffff; padding: 28px 24px; text-align: center;">
      <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;">Mountain Hut</h1>
      <p style="margin: 6px 0 0; color: #94a3b8; font-size: 14px;">Reservation Confirmation</p>
    </div>

    <!-- Body -->
    <div style="padding: 24px;">
      <p style="margin-top: 0; font-size: 16px;">Dear <strong>{hiker_name}</strong>,</p>
      <p style="color: #475569; font-size: 15px; line-height: 1.5;">Your table reservation is confirmed. Here are the details of your booking:</p>

      <!-- Reference Badge -->
      <div style="background-color: #f1f5f9; border-left: 4px solid #3b82f6; padding: 14px 18px; margin: 20px 0; border-radius: 0 8px 8px 0;">
        <span style="font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 600;">Booking Reference</span>
        <div style="font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: 0.5px;">{ref}</div>
      </div>

      <!-- Details Table -->
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 14px;">
        <tr>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; color: #64748b; width: 40%;">Hiker Name</td>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-weight: 600;">{hiker_name}</td>
        </tr>
        <tr>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; color: #64748b;">Date</td>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-weight: 600;">{date_str}</td>
        </tr>
        <tr>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; color: #64748b;">Time Slot</td>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-weight: 600;">{time_slot}</td>
        </tr>
        <tr>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; color: #64748b;">Party Size</td>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-weight: 600;">{party_size} person(s)</td>
        </tr>
        <tr>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; color: #64748b;">Special Requirements</td>
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-weight: 500; color: #334155;">{special_reqs}</td>
        </tr>
      </table>

      <p style="margin-bottom: 0; font-size: 14px; color: #475569;">
        We look forward to seeing you at the hut!<br>
        <strong>The Mountain Hut Team</strong>
      </p>
    </div>

    <!-- Footer -->
    <div style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 24px; text-align: center; font-size: 12px; color: #94a3b8;">
      Mountain Hut Hospitality & Refuge System &bull; Automatic notification &bull; Please do not reply directly to this email
    </div>
  </div>
</body>
</html>"""
    return html


def send_booking_confirmation_email(reservation: ReservationMailDTO) -> Dict[str, Any]:
  """
  Format and dispatch the booking confirmation email to the hiker (MH-03).
  Returns delivery metadata including recipient, subject, text, and html body.
  """
  subject = f"Mountain Hut Booking Confirmation [{reservation.booking_reference}]"
  to_email = reservation.contact_email
  text_content = format_booking_email_text(reservation)
  html_content = format_booking_email_html(reservation)

  message=EmailMessage()
  message["Subject"]=subject
  message["From"]=os.getenv("SMTP_EMAIL")
  message["To"] = to_email

  message.set_content(text_content)
  message.add_alternative(html_content, subtype="html")
  try:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", 587))
    email = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")

    if not all([host, email, password]):
        raise ValueError("Missing SMTP configuration in .env")

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login(email, password)
        server.send_message(message)

    return {
        "status": "SENT",
        "to": to_email,
        "subject": subject,
        "booking_reference": reservation.booking_reference,
        "text_content": text_content,
        "html_content": html_content,
    }
  except Exception as e:
        return {
            "status": "FAILED",
            "to": to_email,
            "subject": subject,
            "booking_reference": reservation.booking_reference,
            "error": str(e)
        }  

