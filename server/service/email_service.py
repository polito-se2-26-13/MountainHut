"""Email Template & Formatting Service (MH-03: Receive Confirmation)."""
from typing import Dict, Any, Optional
from server.models.DAO.reservation import ReservationDAO


def format_booking_email_text(reservation: ReservationDAO) -> str:
    """
    Generate plain text confirmation email for a reservation (MH-03).
    Includes:
    - booking reference
    - date and time slot
    - party size
    - possible party requirements (allergies)
    - name of the hiker who made the reservation
    - assigned tables
    """
    conf = reservation.to_confirmation_dict()
    hiker_name = conf.get("hikerName") or "Valued Guest"
    ref = conf.get("bookingReference") or "N/A"
    date_str = conf.get("date") or "N/A"
    time_slot = conf.get("timeSlot") or "N/A"
    party_size = conf.get("partySize") or 1
    special_reqs = conf.get("specialRequirements") or "None specified"
    tables = conf.get("assignedTables") or []

    table_lines = []
    for t in tables:
        loc = f" ({t['tableLocation']})" if t.get("tableLocation") else ""
        table_lines.append(f"  - Table {t['tableNumber']}{loc}: {t['seatsAssigned']} seat(s)")
    tables_formatted = "\n".join(table_lines) if table_lines else "  - Assigned upon arrival"

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

------------------------------------------------------------
TABLE ASSIGNMENT
------------------------------------------------------------
{tables_formatted}

Note: Sharing tables is standard practice in alpine huts.
If your party exceeds a single table's capacity, you may be
seated across adjacent tables.

------------------------------------------------------------
IMPORTANT INFORMATION FOR YOUR VISIT
------------------------------------------------------------
* Arrival: Please arrive 10 minutes prior to your time slot.
* Modifications: Changes can be made up to 2 hours before the due time.
* Mountain Safety: Mountain weather changes quickly. If your party
  encounters unexpected delays on the trail, please contact the hut team.

We look forward to welcoming you to the hut!

Warm regards,
The Mountain Hut Team
============================================================
"""
    return text.strip()


def format_booking_email_html(reservation: ReservationDAO) -> str:
    """
    Generate a clean, responsive HTML email template for booking confirmation (MH-03).
    """
    conf = reservation.to_confirmation_dict()
    hiker_name = conf.get("hikerName") or "Valued Guest"
    ref = conf.get("bookingReference") or "N/A"
    date_str = conf.get("date") or "N/A"
    time_slot = conf.get("timeSlot") or "N/A"
    party_size = conf.get("partySize") or 1
    special_reqs = conf.get("specialRequirements") or "None specified"
    tables = conf.get("assignedTables") or []

    table_rows = "".join(
        f"<tr><td style='padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-weight: 600;'>Table {t['tableNumber']}</td>"
        f"<td style='padding: 8px 12px; border-bottom: 1px solid #e2e8f0; color: #64748b;'>{t.get('tableLocation', 'Main Hall')}</td>"
        f"<td style='padding: 8px 12px; border-bottom: 1px solid #e2e8f0; text-align: right;'>{t['seatsAssigned']} seat(s)</td></tr>"
        for t in tables
    )
    if not table_rows:
        table_rows = "<tr><td colspan='3' style='padding: 8px 12px; text-align: center; color: #64748b;'>Assigned upon arrival</td></tr>"

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

      <!-- Table Assignment Sub-table -->
      <h3 style="font-size: 15px; margin: 18px 0 10px; color: #0f172a;">Assigned Tables</h3>
      <table style="width: 100%; border-collapse: collapse; background-color: #f8fafc; border-radius: 8px; font-size: 13px; margin-bottom: 24px;">
        <thead>
          <tr style="background-color: #f1f5f9; text-align: left; color: #64748b;">
            <th style="padding: 8px 12px;">Table</th>
            <th style="padding: 8px 12px;">Location</th>
            <th style="padding: 8px 12px; text-align: right;">Seats</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>

      <!-- Note / Guidance -->
      <div style="background-color: #fffbeb; border: 1px solid #fef3c7; border-radius: 8px; padding: 12px 16px; margin-bottom: 24px; font-size: 13px; color: #92400e;">
        <strong>Alpine Hospitality Note:</strong> Table sharing is common at mountain huts. Please arrive 10 minutes prior to your time slot. Changes can be requested up to 2 hours before the slot.
      </div>

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


def send_booking_confirmation_email(reservation: ReservationDAO) -> Dict[str, Any]:
    """
    Format and dispatch the booking confirmation email to the hiker (MH-03).
    Returns delivery metadata including recipient, subject, text, and html body.
    """
    subject = f"Mountain Hut Booking Confirmation [{reservation.booking_reference}]"
    to_email = reservation.contact_email
    text_content = format_booking_email_text(reservation)
    html_content = format_booking_email_html(reservation)

    # In production, SMTP or an email delivery provider (SendGrid, SES, Mailgun) would send it here.
    # We return the email dispatch payload for verification and logging.
    return {
        "status": "SENT",
        "to": to_email,
        "subject": subject,
        "booking_reference": reservation.booking_reference,
        "text_content": text_content,
        "html_content": html_content,
    }

