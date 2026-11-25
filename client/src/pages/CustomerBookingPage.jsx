import { useEffect, useState } from 'react'
import { Button, Checkbox, DatePicker, Form, Input, InputNumber, Select } from 'antd'
import dayjs from 'dayjs'
import { Link, Navigate, useLocation } from 'react-router'
import { apiRequest } from '../api/api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import { useToast } from '../components/ToastProvider.jsx'
import RequirementsEditor, { newRequirement, requirementsBody } from '../components/RequirementsEditor.jsx'
import { formatSlotLabel, getSlotEnd, getSlotId, getSlotStart, isAtLeast, localDateString, normalizeSlots } from '../utils/slots.js'

const TWO_HOURS_MS = 2 * 60 * 60 * 1000

function initialSlotId(availabilitySearch) {
  if (availabilitySearch?.slotId == null) return ''
  return String(availabilitySearch.slotId)
}

function findSelectedSlot(slotOptions, slotOptionsDate, slotDate, slotId) {
  if (slotOptionsDate !== slotDate) return undefined
  return slotOptions.find((slot) => String(getSlotId(slot)) === String(slotId))
}

function getServiceTimePlaceholder(isLoadingSlots, slotCount) {
  if (isLoadingSlots) return 'Loading service times…'
  if (slotCount > 0) return 'Select a time'
  return 'No bookable times for this date'
}

function getContactEmailError(email) {
  const normalizedEmail = email.trim()
  if (!normalizedEmail) return 'Contact email is required.'

  const emailParts = normalizedEmail.split('@')
  if (emailParts.length !== 2 || /\s/.test(normalizedEmail)) return 'Enter a valid email address.'
  const [localPart, domain] = emailParts
  const finalDot = domain.lastIndexOf('.')
  if (!localPart || !domain || finalDot <= 0 || finalDot === domain.length - 1) {
    return 'Enter a valid email address.'
  }
  return ''
}

function getPartySizeError(partySize, availability, remainingSeats) {
  const guestCount = Number(partySize)
  if (!Number.isInteger(guestCount) || guestCount < 1) return 'Party size must be at least 1.'
  if (availability && guestCount > remainingSeats) {
    const seatWord = remainingSeats === 1 ? 'seat' : 'seats'
    return `Only ${remainingSeats} ${seatWord} remain for this time.`
  }
  return ''
}

function getBookingValidationError({
  selectedSlot,
  selectedTimeStillValid,
  availability,
  isSlotOpen,
  isCheckingAvailability,
  partySizeError,
  contactNameError,
  contactEmailError,
  userId,
}) {
  if (!selectedSlot) return 'Choose a service time before continuing.'
  if (!selectedTimeStillValid) return 'Bookings must be made at least 2 hours before the service time.'
  if (!availability || !isSlotOpen || isCheckingAvailability) return 'This service time is not currently available.'
  if (partySizeError || contactNameError || contactEmailError) {
    return partySizeError || contactNameError || contactEmailError
  }
  if (!Number.isInteger(userId) || userId < 1) {
    return 'Your account is missing a valid user ID. Please sign in again.'
  }
  return ''
}

function guestWord(count) {
  return count === 1 ? 'guest' : 'guests'
}

function seatWord(count) {
  return count === 1 ? 'seat' : 'seats'
}

function BookingConfirmation({ bookingSuccessData }) {
  if (!bookingSuccessData) return null

  return (
    <section className="booking-confirmation" aria-labelledby="booking-confirmation-title">
      <div className="confirmation-icon" aria-hidden="true">✓</div>
      <div className="confirmation-content">
        <p className="eyebrow">BOOKING CONFIRMED</p>
        <h2 id="booking-confirmation-title"><output>Your table is reserved</output></h2>
        <p>Reference <strong>{bookingSuccessData.booking_reference}</strong></p>
        <p>{bookingSuccessData.bookingDate} · {bookingSuccessData.bookingTime}–{bookingSuccessData.bookingEndTime} · {bookingSuccessData.bookedPartySize} {guestWord(bookingSuccessData.bookedPartySize)}</p>
        {bookingSuccessData.assigned_tables.length > 0 && (
          <div className="assigned-tables">
            <strong>Assigned seating</strong>
            {bookingSuccessData.assigned_tables.map((table) => (
              <span key={table.table_id}>
                Table {table.table_number} · {table.assigned_seats} {seatWord(table.assigned_seats)}{table.location ? ` · ${table.location}` : ''}
              </span>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function AvailabilityFeedback({ isLoadingSlots, slotOptions, isCheckingAvailability, availability, isSlotOpen, remainingSeats }) {
  if (isLoadingSlots) {
    return <output className="availability-hint">Finding service times for your selected date…</output>
  }
  if (slotOptions.length === 0) {
    return <p className="availability-hint">Only times at least 2 hours from now can be booked.</p>
  }
  if (isCheckingAvailability) {
    return <output className="availability-hint">Checking remaining seats…</output>
  }
  if (!availability) return null

  const isAvailable = isSlotOpen && remainingSeats > 0
  const statusText = isAvailable ? 'Time available' : 'This time is not available'

  return (
    <div className={`availability-card${isAvailable ? '' : ' unavailable'}`}>
      <span className="availability-dot" aria-hidden="true" />
      <output>
        <strong>{statusText}</strong>
        <span>{remainingSeats} {seatWord(remainingSeats)} remaining</span>
      </output>
    </div>
  )
}

function CustomerBookingPage() {
  const { session } = useAuth()
  const location = useLocation()
  const availabilitySearch = location.state?.availabilitySearch
  const [slotDate, setSlotDate] = useState(availabilitySearch?.date || localDateString())
  const [slotOptions, setSlotOptions] = useState([])
  const [slotOptionsDate, setSlotOptionsDate] = useState('')
  const [slotId, setSlotId] = useState(() => initialSlotId(availabilitySearch))
  const [availability, setAvailability] = useState(null)
  const [partySize, setPartySize] = useState(availabilitySearch?.partySize ?? 2)
  const [contactName, setContactName] = useState(session?.userProfile?.fullName || '')
  const accountEmail = session?.userProfile?.email || ''
  const [useAlternativeEmail, setUseAlternativeEmail] = useState(false)
  const [alternativeEmail, setAlternativeEmail] = useState('')
  const contactEmail = useAlternativeEmail ? alternativeEmail : accountEmail
  const [contactPhone, setContactPhone] = useState('')
  const [specialRequirements, setSpecialRequirements] = useState(() => [newRequirement()])
  const [isLoadingSlots, setIsLoadingSlots] = useState(true)
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [bookingSuccessData, setBookingSuccessData] = useState(null)
  const [touched, setTouched] = useState({})
  const notify = useToast()
  const selectedSlot = findSelectedSlot(slotOptions, slotOptionsDate, slotDate, slotId)

  useEffect(() => {
    if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker') return undefined
    let active = true
    apiRequest(`/slots?date=${encodeURIComponent(slotDate)}`, {
      headers: { Authorization: `Bearer ${session.token}` },
    })
      .then((response) => {
        const upcomingSlots = normalizeSlots(response)
          .filter((slot) => isAtLeast(slotDate, getSlotStart(slot), TWO_HOURS_MS))
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
    // after sign out the session is gone and the page is leaving, so nothing to ask
    if (!selectedSlot || !session?.isAuthenticated) return undefined
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

  const remainingSeats = availability?.remaining_seats ?? 0
  const isSlotOpen = availability?.status === 'OPEN'
  const contactNameError = !contactName.trim() ? 'Contact name is required.' : ''
  const contactEmailError = getContactEmailError(contactEmail)
  const partySizeError = getPartySizeError(partySize, availability, remainingSeats)
  const selectedTimeStillValid = selectedSlot && isAtLeast(slotDate, getSlotStart(selectedSlot), TWO_HOURS_MS)
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

    const userId = Number(session.userProfile.id)
    const validationError = getBookingValidationError({
      selectedSlot,
      selectedTimeStillValid,
      availability,
      isSlotOpen,
      isCheckingAvailability,
      partySizeError,
      contactNameError,
      contactEmailError,
      userId,
    })
    if (validationError) {
      notify(validationError)
      return
    }

    const specialRequirementsBody = requirementsBody(specialRequirements)
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
          ...(specialRequirementsBody.length ? { special_requirements: specialRequirementsBody } : {}),
        }),
      })
      setBookingSuccessData({
        ...result,
        bookingDate: slotDate,
        bookingTime: getSlotStart(selectedSlot),
        bookingEndTime: getSlotEnd(selectedSlot),
        bookedPartySize: Number(partySize),
      })
      window.scrollTo({ top: 0, behavior: 'smooth' })
      setSlotId('')
      setAvailability(null)
      setPartySize(2)
      setSpecialRequirements([])
    } catch (error) {
      notify(error.message || 'Your booking could not be completed. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="page booking-page">
      <header className="booking-header">
        <div>
          <Link className="back-link" to="/home/hiker">← Back</Link>
          <p className="eyebrow">MOUNTAINHUT · GUEST BOOKING</p>
          <h1>Book a table</h1>
          <p className="form-intro">Choose a service time, tell us how many are joining, and we’ll take care of the seating.</p>
        </div>
      </header>

      <BookingConfirmation bookingSuccessData={bookingSuccessData} />

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
                  placeholder={getServiceTimePlaceholder(isLoadingSlots, slotOptions.length)}
                  loading={isLoadingSlots}
                  onChange={(value) => { setSlotId(value); setAvailability(null); setIsCheckingAvailability(Boolean(value)); clearBookingConfirmation() }}
                  disabled={isLoadingSlots || slotOptions.length === 0}
                  options={slotOptions.map((slot) => ({ value: String(getSlotId(slot)), label: formatSlotLabel(slot) }))}
                />
              </label>
            </div>
            <AvailabilityFeedback
              isLoadingSlots={isLoadingSlots}
              slotOptions={slotOptions}
              isCheckingAvailability={isCheckingAvailability}
              availability={availability}
              isSlotOpen={isSlotOpen}
              remainingSeats={remainingSeats}
            />
          </section>

          <section className="booking-panel" aria-labelledby="party-size-title">
            <div className="booking-panel-heading">
              <span className="section-step">02</span>
              <div><h2 id="party-size-title">Your party</h2><p>We’ll arrange the table or tables for your group.</p></div>
            </div>
            <label className="form-field party-size-field">
              <span>Number of guests <span className="required-mark" aria-hidden="true">*</span></span>
              <InputNumber className="mh-control" min={1} step={1} value={partySize} onChange={(value) => { setPartySize(value ?? ''); clearBookingConfirmation() }} onBlur={() => setTouched((current) => ({ ...current, partySize: true }))} aria-invalid={Boolean(touched.partySize && partySizeError)} />
              {touched.partySize && partySizeError && <small className="field-error">{partySizeError}</small>}
              {availability && !partySizeError && <small className="field-hint">Up to {remainingSeats} guests can be booked for this time.</small>}
            </label>
          </section>

          <section className="booking-panel" aria-labelledby="requirements-title">
            <div className="booking-panel-heading">
              <span className="section-step">03</span>
              <div><h2 id="requirements-title">Special requirements <span className="optional-mark">(optional)</span></h2><p>Share dietary needs or allergies for your group.</p></div>
            </div>
            <div className="booking-fields">
              <div className="form-field form-field-wide requirements-field">
                <RequirementsEditor requirements={specialRequirements} onChange={(requirements) => { setSpecialRequirements(requirements); clearBookingConfirmation() }} />
              </div>
            </div>
          </section>

          <section className="booking-panel" aria-labelledby="contact-title">
            <div className="booking-panel-heading">
              <span className="section-step">04</span>
              <div><h2 id="contact-title">Contact details</h2><p>We’ll send your booking confirmation to this email.</p></div>
            </div>
            <div className="booking-fields">
              <label className="form-field">
                <span>Contact name <span className="required-mark" aria-hidden="true">*</span></span>
                <Input className="mh-control" value={contactName} autoComplete="name" onChange={(event) => { setContactName(event.target.value); clearBookingConfirmation() }} onBlur={() => setTouched((current) => ({ ...current, contactName: true }))} aria-invalid={Boolean(touched.contactName && contactNameError)} />
                {touched.contactName && contactNameError && <small className="field-error">{contactNameError}</small>}
              </label>
              <div className="form-field form-field-wide">
                <span>Confirmation email</span>
                <p className="field-hint">By default, we’ll send the confirmation to your account email: <strong>{accountEmail || 'No account email available'}</strong></p>
                <Checkbox checked={useAlternativeEmail} onChange={(event) => {
                  setUseAlternativeEmail(event.target.checked)
                  setTouched((current) => ({ ...current, contactEmail: false }))
                  clearBookingConfirmation()
                }}>
                  I want to send the confirmation to a different email address.
                </Checkbox>
                {useAlternativeEmail && (
                  <label className="form-field alternative-email-field">
                    <span>Alternative email <span className="required-mark" aria-hidden="true">*</span></span>
                    <Input className="mh-control" type="email" value={alternativeEmail} autoComplete="email" onChange={(event) => { setAlternativeEmail(event.target.value); clearBookingConfirmation() }} onBlur={() => setTouched((current) => ({ ...current, contactEmail: true }))} aria-invalid={Boolean(touched.contactEmail && contactEmailError)} />
                    {touched.contactEmail && contactEmailError && <small className="field-error">{contactEmailError}</small>}
                  </label>
                )}
              </div>
              <label className="form-field">
                <span>Phone <span className="optional-mark">(optional)</span></span>
                <Input className="mh-control" type="tel" value={contactPhone} autoComplete="tel" onChange={(event) => { setContactPhone(event.target.value); clearBookingConfirmation() }} />
              </label>
            </div>
          </section>
        </div>

        <aside className="booking-summary" aria-label="Booking summary">
          <p className="eyebrow">YOUR BOOKING</p>
          <h2>Mountain Hut</h2>
          <div className="summary-divider" />
          <div className="summary-line"><span>Date</span><strong>{slotDate || 'Choose a date'}</strong></div>
          <div className="summary-line"><span>Time</span><strong>{selectedSlot ? `${getSlotStart(selectedSlot)} – ${getSlotEnd(selectedSlot)}` : 'Choose a time'}</strong></div>
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
