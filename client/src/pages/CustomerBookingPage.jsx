import { useEffect, useState } from 'react'
import { Button, DatePicker, Form, Input, InputNumber, Select } from 'antd'
import dayjs from 'dayjs'
import { Link, Navigate, useNavigate } from 'react-router'
import { apiRequest } from '../api/api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import { useToast } from '../components/ToastProvider.jsx'

const TWO_HOURS_MS = 2 * 60 * 60 * 1000

function localDateString() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

function normalizeSlots(response) {
  if (Array.isArray(response)) return response
  if (Array.isArray(response?.slots)) return response.slots
  if (Array.isArray(response?.items)) return response.items
  return []
}

function getSlotId(slot) {
  return slot.slot_id ?? slot.slotId ?? slot.id
}

function getSlotStart(slot) {
  return slot.start_time ?? slot.startTime ?? slot.time
}

function getSlotEnd(slot) {
  return slot.end_time ?? slot.endTime ?? ''
}

function isMoreThanTwoHoursAway(date, time) {
  if (!date || !time) return false
  const slotTime = new Date(`${date}T${time}:00`).getTime()
  return Number.isFinite(slotTime) && slotTime - Date.now() >= TWO_HOURS_MS
}

function formatAssignedTables(tables = []) {
  return tables.map((table) => ({
    tableNumber: table.table_number ?? table.tableNumber ?? '—',
    seats: table.assigned_seats ?? table.assignedSeats ?? 0,
    location: table.location ?? table.tableLocation,
  }))
}

function CustomerBookingPage() {
  const { session } = useAuth()
  const [slotDate, setSlotDate] = useState(localDateString())
  const [slotOptions, setSlotOptions] = useState([])
  const [slotOptionsDate, setSlotOptionsDate] = useState('')
  const [slotId, setSlotId] = useState('')
  const [availability, setAvailability] = useState(null)
  const [partySize, setPartySize] = useState(2)
  const [contactName, setContactName] = useState(session?.userProfile?.fullName || '')
  const [contactEmail, setContactEmail] = useState(session?.userProfile?.email || '')
  const [contactPhone, setContactPhone] = useState('')
  const [specialReqs, setSpecialReqs] = useState('')
  const [isLoadingSlots, setIsLoadingSlots] = useState(true)
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [bookingSuccessData, setBookingSuccessData] = useState(null)
  const [touched, setTouched] = useState({})
  const notify = useToast()
  const navigate = useNavigate()
  const selectedSlot = slotOptionsDate === slotDate
    ? slotOptions.find((slot) => String(getSlotId(slot)) === String(slotId))
    : undefined

  useEffect(() => {
    if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker') return undefined
    let active = true
    apiRequest(`/slots?date=${encodeURIComponent(slotDate)}`, {
      headers: { Authorization: `Bearer ${session.token}` },
    })
      .then((response) => {
        const upcomingSlots = normalizeSlots(response)
          .filter((slot) => getSlotId(slot) != null && isMoreThanTwoHoursAway(slotDate, getSlotStart(slot)))
          .sort((a, b) => getSlotStart(a).localeCompare(getSlotStart(b)))
        if (active) {
          setSlotOptions(upcomingSlots)
          setSlotOptionsDate(slotDate)
        }
        return upcomingSlots
      })
      .catch((error) => {
        if (active) notify(error.message || 'Could not load service times for this date.')
        return []
      })
      .finally(() => {
        if (active) setIsLoadingSlots(false)
      })
    return () => { active = false }
  }, [slotDate, session, notify])

  useEffect(() => {
    if (!selectedSlot) return undefined
    let active = true
    apiRequest(`/slots/${encodeURIComponent(getSlotId(selectedSlot))}/availability`, {
      headers: { Authorization: `Bearer ${session.token}` },
    })
      .then((result) => {
        if (active) setAvailability(result)
      })
      .catch((error) => {
        if (active) notify(error.message || 'Could not check remaining seats for this time.')
      })
      .finally(() => {
        if (active) setIsCheckingAvailability(false)
      })
    return () => { active = false }
  }, [selectedSlot, session, notify])

  const remainingSeats = Number(availability?.remaining_seats ?? availability?.remainingSeats ?? 0)
  const isSlotOpen = (availability?.status || '').toUpperCase() === 'OPEN'
  const contactNameError = !contactName.trim() ? 'Contact name is required.' : ''
  const contactEmailError = !contactEmail.trim()
    ? 'Contact email is required.'
    : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contactEmail.trim())
      ? 'Enter a valid email address.'
      : ''
  const partySizeError = !Number.isInteger(Number(partySize)) || Number(partySize) < 1
    ? 'Party size must be at least 1.'
    : availability && Number(partySize) > remainingSeats
      ? `Only ${remainingSeats} seat${remainingSeats === 1 ? '' : 's'} remain for this time.`
      : ''
  const selectedTimeStillValid = selectedSlot && isMoreThanTwoHoursAway(slotDate, getSlotStart(selectedSlot))
  const canSubmit = Boolean(
    selectedSlot && selectedTimeStillValid && availability && isSlotOpen && !isCheckingAvailability
    && !partySizeError && !contactNameError && !contactEmailError,
  )

  if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker') {
    return <Navigate to="/login" replace />
  }

  function handleDateChange(value) {
    setIsLoadingSlots(true)
    setSlotOptions([])
    setSlotOptionsDate('')
    setSlotId('')
    setAvailability(null)
    setIsCheckingAvailability(false)
    setSlotDate(value)
    setBookingSuccessData(null)
  }

  function clearBookingConfirmation() {
    setBookingSuccessData(null)
  }

  async function handleSubmit() {
    setTouched({ partySize: true, contactName: true, contactEmail: true })
    setBookingSuccessData(null)

    if (!selectedSlot) {
      notify('Choose a service time before continuing.')
      return
    }
    if (!selectedTimeStillValid) {
      notify('Bookings must be made at least 2 hours before the service time.')
      return
    }
    if (!availability || !isSlotOpen || isCheckingAvailability) {
      notify('This service time is not currently available.')
      return
    }
    if (partySizeError || contactNameError || contactEmailError) {
      notify(partySizeError || contactNameError || contactEmailError)
      return
    }
    const userId = Number(session.userProfile.id)
    if (!Number.isInteger(userId) || userId < 1) {
      notify('Your account is missing a valid user ID. Please sign in again.')
      return
    }

    setIsSubmitting(true)
    try {
      const result = await apiRequest('/reservations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.token}`,
        },
        body: JSON.stringify({
          slot_id: Number(getSlotId(selectedSlot)),
          party_size: Number(partySize),
          user_id: userId,
          contact_name: contactName.trim(),
          contact_email: contactEmail.trim(),
          ...(contactPhone.trim() ? { contact_phone: contactPhone.trim() } : {}),
          ...(specialReqs.trim() ? { special_requirements: specialReqs.trim() } : {}),
        }),
      })
      setBookingSuccessData({
        ...result,
        bookingDate: slotDate,
        bookingTime: getSlotStart(selectedSlot),
        bookingEndTime: getSlotEnd(selectedSlot),
        bookedPartySize: Number(partySize),
      })
      setSlotId('')
      setAvailability(null)
      setPartySize(2)
      setSpecialReqs('')
    } catch (error) {
      notify(error.message || 'Your booking could not be completed. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const assignedTables = formatAssignedTables(bookingSuccessData?.assigned_tables || bookingSuccessData?.assignedTables || [])

  return (
    <main className="page booking-page">
      <header className="booking-header">
        <div>
          <button className="back-link" type="button" onClick={() => window.history.length > 1 ? navigate(-1) : navigate('/home/hiker')}>
            ← Back
          </button>
          <p className="eyebrow">MOUNTAINHUT · GUEST BOOKING</p>
          <h1>Book a table</h1>
          <p className="form-intro">Choose a service time, tell us how many are joining, and we’ll take care of the seating.</p>
        </div>
        <div className="booking-header-mark" aria-hidden="true">MH</div>
      </header>

      {bookingSuccessData && (
        <section className="booking-confirmation" role="status" aria-labelledby="booking-confirmation-title">
          <div className="confirmation-icon" aria-hidden="true">✓</div>
          <div className="confirmation-content">
            <p className="eyebrow">BOOKING CONFIRMED</p>
            <h2 id="booking-confirmation-title">Your table is reserved</h2>
            <p>Reference <strong>{bookingSuccessData.booking_reference || '—'}</strong></p>
            <p>{bookingSuccessData.bookingDate} · {bookingSuccessData.bookingTime}{bookingSuccessData.bookingEndTime ? `–${bookingSuccessData.bookingEndTime}` : ''} · {bookingSuccessData.bookedPartySize} guest{bookingSuccessData.bookedPartySize === 1 ? '' : 's'}</p>
            {assignedTables.length > 0 && (
              <div className="assigned-tables">
                <strong>Assigned seating</strong>
                {assignedTables.map((table, index) => (
                  <span key={`${table.tableNumber}-${index}`}>
                    Table {table.tableNumber} · {table.seats} seat{table.seats === 1 ? '' : 's'}{table.location ? ` · ${table.location}` : ''}
                  </span>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      <Form className="booking-layout mh-form" onFinish={handleSubmit} noValidate>
        <div className="booking-main-column">
          <section className="booking-panel" aria-labelledby="choose-time-title">
            <div className="booking-panel-heading">
              <span className="section-step">01</span>
              <div><h2 id="choose-time-title">Choose your service</h2><p>Select a date and an available time.</p></div>
            </div>
            <div className="booking-fields booking-time-fields">
              <label className="form-field">
                <span>Date <span className="required-mark" aria-hidden="true">*</span></span>
                <DatePicker
                  className="mh-control"
                  format="YYYY-MM-DD"
                  value={slotDate ? dayjs(slotDate) : null}
                  disabledDate={date => date.isBefore(dayjs(localDateString()), 'day')}
                  onChange={date => handleDateChange(date ? date.format('YYYY-MM-DD') : '')}
                  allowClear={false}
                />
              </label>
              <label className="form-field">
                <span>Service time <span className="required-mark" aria-hidden="true">*</span></span>
                <Select
                  className="mh-control"
                  value={slotId || undefined}
                  placeholder={isLoadingSlots ? 'Loading service times…' : slotOptions.length ? 'Select a time' : 'No bookable times for this date'}
                  loading={isLoadingSlots}
                  onChange={(value) => { setSlotId(value); setAvailability(null); setIsCheckingAvailability(Boolean(value)); clearBookingConfirmation() }}
                  disabled={isLoadingSlots || slotOptions.length === 0}
                  options={slotOptions.map((slot) => {
                    const start = getSlotStart(slot)
                    const end = getSlotEnd(slot)
                    const meal = slot.meal_type ?? slot.mealType
                    return {
                      value: String(getSlotId(slot)),
                      label: `${start}${end ? ` – ${end}` : ''}${meal ? ` · ${meal}` : ''}`,
                    }
                  })}
                />
              </label>
            </div>
            {isLoadingSlots && <p className="availability-hint">Finding service times for your selected date…</p>}
            {!isLoadingSlots && slotOptions.length === 0 && <p className="availability-hint">Only times at least 2 hours from now can be booked.</p>}
            {isCheckingAvailability && <p className="availability-hint" role="status">Checking remaining seats…</p>}
            {availability && (
              <div className={`availability-card${isSlotOpen && remainingSeats > 0 ? '' : ' unavailable'}`} role="status">
                <span className="availability-dot" aria-hidden="true" />
                <div><strong>{isSlotOpen && remainingSeats > 0 ? 'Time available' : 'This time is not available'}</strong><span>{remainingSeats} seat{remainingSeats === 1 ? '' : 's'} remaining</span></div>
              </div>
            )}
          </section>

          <section className="booking-panel" aria-labelledby="party-size-title">
            <div className="booking-panel-heading">
              <span className="section-step">02</span>
              <div><h2 id="party-size-title">Your party</h2><p>We’ll arrange the table or tables for your group.</p></div>
            </div>
            <label className="form-field party-size-field">
              <span>Number of guests <span className="required-mark" aria-hidden="true">*</span></span>
              <InputNumber className="mh-control" min={1} max={availability ? remainingSeats : undefined} step={1} value={partySize} onChange={(value) => { setPartySize(value ?? ''); clearBookingConfirmation() }} onBlur={() => setTouched((current) => ({ ...current, partySize: true }))} aria-invalid={Boolean(touched.partySize && partySizeError)} />
              {touched.partySize && partySizeError && <small className="field-error">{partySizeError}</small>}
              {availability && !partySizeError && <small className="field-hint">Up to {remainingSeats} guests can be booked for this time.</small>}
            </label>
          </section>

          <section className="booking-panel" aria-labelledby="contact-title">
            <div className="booking-panel-heading">
              <span className="section-step">03</span>
              <div><h2 id="contact-title">Contact details</h2><p>We’ll send your booking confirmation to this email.</p></div>
            </div>
            <div className="booking-fields">
              <label className="form-field">
                <span>Contact name <span className="required-mark" aria-hidden="true">*</span></span>
                <Input className="mh-control" value={contactName} autoComplete="name" onChange={(event) => { setContactName(event.target.value); clearBookingConfirmation() }} onBlur={() => setTouched((current) => ({ ...current, contactName: true }))} aria-invalid={Boolean(touched.contactName && contactNameError)} />
                {touched.contactName && contactNameError && <small className="field-error">{contactNameError}</small>}
              </label>
              <label className="form-field">
                <span>Email <span className="required-mark" aria-hidden="true">*</span></span>
                <Input className="mh-control" type="email" value={contactEmail} autoComplete="email" onChange={(event) => { setContactEmail(event.target.value); clearBookingConfirmation() }} onBlur={() => setTouched((current) => ({ ...current, contactEmail: true }))} aria-invalid={Boolean(touched.contactEmail && contactEmailError)} />
                {touched.contactEmail && contactEmailError && <small className="field-error">{contactEmailError}</small>}
              </label>
              <label className="form-field">
                <span>Phone <span className="optional-mark">(optional)</span></span>
                <Input className="mh-control" type="tel" value={contactPhone} autoComplete="tel" onChange={(event) => { setContactPhone(event.target.value); clearBookingConfirmation() }} />
              </label>
              <label className="form-field form-field-wide">
                <span>Special requirements <span className="optional-mark">(optional)</span></span>
                <Input.TextArea className="mh-control" rows={4} value={specialReqs} placeholder="Dietary needs, allergies, or anything else we should know" onChange={(event) => { setSpecialReqs(event.target.value); clearBookingConfirmation() }} />
              </label>
            </div>
          </section>
        </div>

        <aside className="booking-summary" aria-label="Booking summary">
          <p className="eyebrow">YOUR BOOKING</p>
          <h2>Mountain Hut</h2>
          <div className="summary-divider" />
          <div className="summary-line"><span>Date</span><strong>{slotDate || 'Choose a date'}</strong></div>
          <div className="summary-line"><span>Time</span><strong>{selectedSlot ? `${getSlotStart(selectedSlot)}${getSlotEnd(selectedSlot) ? ` – ${getSlotEnd(selectedSlot)}` : ''}` : 'Choose a time'}</strong></div>
          <div className="summary-line"><span>Guests</span><strong>{partySize || 0}</strong></div>
          {availability && <div className="summary-line"><span>Seats left</span><strong>{remainingSeats}</strong></div>}
          <p className="summary-note">Reservations must be made at least 2 hours before the service time.</p>
          <Button className="submit-button booking-submit" type="primary" htmlType="submit" disabled={!canSubmit || isSubmitting} loading={isSubmitting}>
            {isSubmitting ? 'Confirming booking…' : 'Confirm booking'}
          </Button>
          {!canSubmit && !isSubmitting && <small className="submit-hint">Select an available time and enter valid guest and contact details to continue.</small>}
          <Link className="summary-back-link" to="/home/hiker">Back to home</Link>
        </aside>
      </Form>
    </main>
  )
}

export default CustomerBookingPage
