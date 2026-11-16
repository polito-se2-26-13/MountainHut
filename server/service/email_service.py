"""Email Template & Formatting Service (MH-03: Receive Confirmation)."""
from html import escape
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

def _as_mail_dto(reservation: ReservationMailDTO | ReservationDAO) -> ReservationMailDTO:
    if isinstance(reservation, ReservationMailDTO):
        return reservation

    assigned_tables = [
        {
            "table_number": assignment.slot_table.table.table_number,
            "assigned_seats": assignment.assigned_seats,
        }
        for assignment in reservation.table_assignments
        if assignment.slot_table and assignment.slot_table.table
    ]
    return ReservationMailDTO(
        hiker_name=reservation.contact_name,
        booking_reference=reservation.booking_reference,
        contact_email=reservation.contact_email,
        date_str=reservation.slot.date.isoformat(),
        time_slot=f"{reservation.slot.start_time:%H:%M} - {reservation.slot.end_time:%H:%M}",
        party_size=reservation.party_size,
        special_reqs=reservation.special_requirements,
        assigned_tables=assigned_tables,
    )


def format_booking_email_text(reservation: ReservationMailDTO | ReservationDAO) -> str:
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
"""
    reservation = _as_mail_dto(reservation)
    hiker_name=reservation.hiker_name
    ref= reservation.booking_reference
    date_str = reservation.date_str
    time_slot = reservation.time_slot
    party_size = reservation.party_size
    raw_reqs = reservation.special_reqs or ""

    # Build a human-readable block; lines that start with [ALLERGY WARNING] are flagged
    if raw_reqs:
        req_lines = [r.strip() for r in raw_reqs.split(";") if r.strip()]
        req_block = "\n".join(f"  • {line}" for line in req_lines)
    else:
        req_block = "  None specified"
    table_block = "\n".join(
        f"  Table {table['table_number']}: {table['assigned_seats']} seat(s)"
        for table in reservation.assigned_tables
    )

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
* Special Requirements:
{req_block}"""
    if table_block:
        text += f"""
* Assigned Tables:
{table_block}"""

    text += """

We look forward to welcoming you to the hut!

Warm regards,
The Mountain Hut Team
============================================================
"""
    return text.strip()


def format_booking_email_html(reservation: ReservationMailDTO | ReservationDAO) -> str:
    """
    Generate a clean, responsive HTML email template for booking confirmation (MH-03).
    """
    reservation = _as_mail_dto(reservation)
    # name and requests are typed by the user: escaped, so they reach the mail as text and not as HTML or links
    hiker_name=escape(reservation.hiker_name)
    ref= reservation.booking_reference
    date_str = reservation.date_str
    time_slot = reservation.time_slot
    party_size = reservation.party_size
    raw_reqs = reservation.special_reqs or ""

    # Build structured HTML rows for each requirement (MH-05)
    if raw_reqs:
        req_items = [escape(r.strip()) for r in raw_reqs.split(";") if r.strip()]
        req_rows = ""
        for item in req_items:
            if item.startswith("[ALLERGY WARNING]"):
                label = item[len("[ALLERGY WARNING]"):].strip()
                req_rows += (
                    f'<li style="color:#c2410c;font-weight:600;">'
                    f'⚠️ <span style="background:#fff7ed;padding:2px 6px;border-radius:4px;">'
                    f'[ALLERGY WARNING]</span> {label}</li>'
                )
            else:
                req_rows += f'<li style="color:#334155;">{item}</li>'
        req_html = f'<ul style="margin:4px 0 0 16px;padding:0;font-size:14px;">{req_rows}</ul>'
    else:
        req_html = '<span style="color:#94a3b8;font-size:14px;">None specified</span>'
    tables_html = "".join(
        f"<li>Table {escape(str(table['table_number']))}: {table['assigned_seats']} seat(s)</li>"
        for table in reservation.assigned_tables
    )
    tables_row = (
        f"""<tr>
          <td style="padding: 10px 0; color: #64748b;">Assigned Tables</td>
          <td style="padding: 10px 0; font-weight: 500; color: #334155;"><ul>{tables_html}</ul></td>
        </tr>"""
        if tables_html
        else ""
    )
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
          <td style="padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-weight: 500; color: #334155;">{req_html}</td>
        </tr>
        {tables_row}
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

def send_booking_confirmation_email(reservation: ReservationMailDTO | ReservationDAO) -> Dict[str, Any]:
  reservation = _as_mail_dto(reservation)
  subject = f"Mountain Hut Booking Confirmation [{reservation.booking_reference}]"
  to_email = reservation.contact_email
  text_content = format_booking_email_text(reservation)
  html_content = format_booking_email_html(reservation)
  return sender_email(subject,to_email,text_content,html_content,reservation.booking_reference)


def send_booking_change_email(
    reservation: ReservationMailDTO | ReservationDAO,
    previous_slot: str,
    previous_party_size: int,
) -> Dict[str, Any]:
  reservation = _as_mail_dto(reservation)
  subject = f"Mountain Hut Booking Changed [{reservation.booking_reference}]"
  text_content = format_booking_email_text(reservation)
  text_content += (
      f"\n\nThis booking was changed from {previous_slot}, "
      f"{previous_party_size} person(s).\n"
  )
  html_content = format_booking_email_html(reservation)
  html_content += (
      f"<p>This booking was changed from {escape(previous_slot)}, "
      f"{previous_party_size} person(s).</p>"
  )
  return sender_email(subject, reservation.contact_email, text_content, html_content, reservation.booking_reference)

def sender_email(subject:str,to_email:str,text_content:str,html_content:str,booking_ref:str) -> Dict[str, Any]:
  """
  Format and dispatch the booking confirmation email to the hiker (MH-03).
  Returns delivery metadata including recipient, subject, text, and html body.
  """
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
        "booking_reference": booking_ref,
        "text_content": text_content,
        "html_content": html_content,
    }
  except Exception as e:
        return {
            "status": "FAILED",
            "to": to_email,
            "subject": subject,
            "booking_reference": booking_ref,
            "error": str(e)
        }  

