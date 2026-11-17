import { useState } from 'react'
import { Button, DatePicker, InputNumber, TimePicker } from 'antd'
import dayjs from 'dayjs'
import { Link } from 'react-router'
import { apiRequest } from '../api/api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import { isAtLeast, localDateString } from '../utils/slots.js'

const TWO_HOURS_MS = 2 * 60 * 60 * 1000

function AvailabilityPage() {
  const { session } = useAuth()
  const [date, setDate] = useState(localDateString())
  const [time, setTime] = useState('')
  const [partySize, setPartySize] = useState(2)
  const [searching, setSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function searchAvailability(event) {
    event.preventDefault()
    setHasSearched(true)
    setResult(null)
    setError('')
    if (!date) { setError('Choose a date to continue.'); return }
    if (!time) { setError('Choose a service time to continue.'); return }
    if (!Number.isInteger(Number(partySize)) || Number(partySize) < 1) { setError('Party size must be at least 1.'); return }
    setSearching(true)
    try {
      const query = new URLSearchParams({ date, time, party_size: String(partySize) })
      const response = await apiRequest(`/slots/availability?${query.toString()}`)
      setResult(response)
    } catch (requestError) {
      setError(requestError.status === 404 ? 'That service time could not be found. Choose another time and try again.' : requestError.message || 'Availability could not be checked. Please try again.')
    } finally {
      setSearching(false)
    }
  }

  // bookings close 2 hours before the service (PO #7), so a closer time is not offered as available
  const bookingClosed = Boolean(result) && !isAtLeast(result.date, result.start_time, TWO_HOURS_MS)
  const isAvailable = !bookingClosed && Boolean(result?.is_available)
  const layout = result?.layout ?? []
  const bookingPath = session?.isAuthenticated && session.userProfile.role === 'Hiker' ? '/customer/book-table' : '/login'

  return (
    <main className="page availability-page">
      <header className="booking-header">
        <div>
          <Link className="back-link" to={session?.isAuthenticated ? `/home/${session.userProfile.role.toLowerCase()}` : '/'}>← Back</Link>
          <p className="eyebrow">MOUNTAINHUT · PLAN YOUR VISIT</p>
          <h1>Check availability</h1>
          <p className="form-intro">Choose a date, service time, and group size to see whether we can seat your party.</p>
        </div>
        <div className="booking-header-mark" aria-hidden="true">MH</div>
      </header>

      <form className="availability-search booking-panel" onSubmit={searchAvailability} noValidate>
        <div className="booking-panel-heading">
          <span className="section-step">01</span>
          <div><h2>Find a service time</h2><p>Availability is checked live and is open to everyone.</p></div>
        </div>
        <div className="booking-fields availability-fields">
          <label className="form-field">
            <span>Date <span className="required-mark" aria-hidden="true">*</span></span>
            <DatePicker className="mh-control" format="YYYY-MM-DD" value={date ? dayjs(date) : null}
              disabledDate={(value) => value.isBefore(dayjs(localDateString()), 'day')}
              onChange={(value) => { setDate(value?.format('YYYY-MM-DD') || ''); setResult(null); setError('') }} allowClear={false} />
          </label>
          <label className="form-field">
            <span>Service time <span className="required-mark" aria-hidden="true">*</span></span>
            <TimePicker className="mh-control" format="HH:mm" minuteStep={15}
              value={time ? dayjs(`2000-01-01T${time}`) : null}
              onChange={(value) => { setTime(value?.format('HH:mm') || ''); setResult(null); setError('') }} />
          </label>
          <label className="form-field">
            <span>Party size <span className="required-mark" aria-hidden="true">*</span></span>
            <InputNumber className="mh-control" min={1} step={1} value={partySize} onChange={(value) => { setPartySize(value ?? ''); setResult(null); setError('') }} />
          </label>
        </div>
        {error && <p className="field-error availability-error" role="alert">{error}</p>}
        <Button className="submit-button availability-submit" htmlType="submit" loading={searching}>Check availability</Button>
      </form>

      {result && (
        <section className={`availability-result${isAvailable ? '' : ' unavailable'}`} role="status" aria-live="polite">
          <span className="availability-result-icon" aria-hidden="true">{isAvailable ? '✓' : '!'}</span>
          <div className="availability-result-content">
            <p className="eyebrow">{isAvailable ? 'GOOD NEWS' : bookingClosed ? 'BOOKINGS CLOSED' : 'NO SPACE FOR THIS PARTY'}</p>
            <h2>{isAvailable ? 'There is availability' : bookingClosed ? 'This service can no longer be booked' : 'Not enough seats available'}</h2>
            <p>{bookingClosed
              ? 'Bookings close 2 hours before the service. You can try another date or time.'
              : isAvailable
              ? `Your party of ${result.party_size} can be seated for ${result.start_time}–${result.end_time}. ${result.remaining_seats} seat${result.remaining_seats === 1 ? '' : 's'} remain.`
              : `There are ${result.remaining_seats} seat${result.remaining_seats === 1 ? '' : 's'} remaining for this service, which is not enough for ${result.party_size}. You can try another date or time.`}</p>
            {isAvailable && result.layout_summary && <p className="layout-summary"><strong>Seating preview:</strong> {result.layout_summary}</p>}
            {isAvailable && layout.length > 0 && <ul className="availability-layout">
              {layout.map((table) => <li key={table.table_number}>
                <strong>Table {table.table_number}</strong>
                <span>{table.assigned_seats} seat{table.assigned_seats === 1 ? '' : 's'}{table.location ? ` · ${table.location}` : ''}</span>
              </li>)}
            </ul>}
            {isAvailable && <Link className="submit-button availability-book"
              to={bookingPath}
              state={{ availabilitySearch: {
                date: result.date,
                partySize: result.party_size,
                slotId: result.slot_id,
              } }}>
              {bookingPath === '/login' ? 'Sign in to book' : 'Book now'} <span aria-hidden="true">→</span>
            </Link>}
          </div>
        </section>
      )}
      {!hasSearched && <p className="availability-footnote">Checking availability does not reserve seats. Complete a booking to secure your table.</p>}
    </main>
  )
}

export default AvailabilityPage
