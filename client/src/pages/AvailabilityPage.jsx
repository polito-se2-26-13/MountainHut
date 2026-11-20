import { useEffect, useState } from 'react'
import { DatePicker, InputNumber } from 'antd'
import dayjs from 'dayjs'
import { Link } from 'react-router'
import { apiRequest } from '../api/api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import { isAtLeast, localDateString, normalizeSlots } from '../utils/slots.js'

const TWO_HOURS_MS = 2 * 60 * 60 * 1000

function AvailabilityPage() {
  const { session } = useAuth()
  const [date, setDate] = useState(localDateString())
  const [partySize, setPartySize] = useState(2)
  const [availabilityResult, setAvailabilityResult] = useState(null)
  const [selected, setSelected] = useState(null)
  const requestKey = `${date}:${partySize}`
  const isCurrentResult = availabilityResult?.key === requestKey
  const slots = isCurrentResult ? availabilityResult.slots : []
  const loading = !isCurrentResult
  const error = isCurrentResult ? availabilityResult.error : ''
  const selectedSlot = selected?.key === requestKey ? selected.slot : null
  const bookingPath = session?.isAuthenticated && session.userProfile.role === 'Hiker' ? '/customer/book-table' : '/login'

  useEffect(() => {
    let active = true
    const query = new URLSearchParams({ date, party_size: String(partySize) })
    async function loadAvailability() {
      try {
        const response = await apiRequest(`/slots/availability?${query.toString()}`)
        const availabilityList = normalizeSlots(response)
        const available = availabilityList
          .filter((slot) => slot.is_available && isAtLeast(slot.date, slot.start_time, TWO_HOURS_MS))
          .sort((a, b) => a.start_time.localeCompare(b.start_time))
        if (active) setAvailabilityResult({ key: requestKey, slots: available, error: '' })
      } catch (requestError) {
        if (active) setAvailabilityResult({
          key: requestKey,
          slots: [],
          error: requestError.message || 'Service times could not be loaded. Please try again.',
        })
      }
    }
    void loadAvailability()
    return () => { active = false }
  }, [date, partySize, requestKey])

  let slotContent
  if (loading) {
    slotContent = <output className="availability-empty">Loading available times…</output>
  } else if (slots.length === 0) {
    slotContent = <output className="availability-empty">No available service times for {date}. Choose another date or group size.</output>
  } else {
    slotContent = (
      <ul className="availability-slot-list">
        {slots.map((slot) => {
          const active = selectedSlot && slot.slot_id === selectedSlot.slot_id
          return <li key={slot.slot_id}>
            <button className={`availability-slot${active ? ' selected' : ''}`} type="button"
              aria-pressed={Boolean(active)} onClick={() => setSelected({ key: requestKey, slot })}>
              <span><strong>{slot.start_time}–{slot.end_time}</strong>{slot.meal_type && <small>{slot.meal_type}</small>}</span>
              <span className="availability-slot-seats">{slot.remaining_seats} seats left <span aria-hidden="true">→</span></span>
            </button>
          </li>
        })}
      </ul>
    )
  }

  return (
    <main className="page availability-page">
      <header className="booking-header">
        <div>
          <Link className="back-link" to={session?.isAuthenticated ? `/home/${session.userProfile.role.toLowerCase()}` : '/'}>← Back</Link>
          <p className="eyebrow">MOUNTAINHUT · PLAN YOUR VISIT</p>
          <h1>Check availability</h1>
          <p className="form-intro">Choose a date and group size to see available service times.</p>
        </div>
        <div className="booking-header-mark" aria-hidden="true">MH</div>
      </header>

      <section className="availability-search booking-panel" aria-labelledby="availability-slots-title">
        <div className="booking-panel-heading">
          <span className="section-step">01</span>
          <div><h2 id="availability-slots-title">Available service times</h2><p>Select a time to see seating details and continue to booking.</p></div>
        </div>
        <div className="booking-fields availability-fields availability-filter-fields">
          <label className="form-field">
            <span>Date</span>
            <DatePicker className="mh-control" format="YYYY-MM-DD" value={date ? dayjs(date) : null}
              disabledDate={(value) => value.isBefore(dayjs(localDateString()), 'day')}
              onChange={(value) => setDate(value?.format('YYYY-MM-DD') || localDateString())} allowClear={false} />
          </label>
          <label className="form-field">
            <span>Party size</span>
            <InputNumber className="mh-control" min={1} step={1} value={partySize} onChange={(value) => setPartySize(value ?? 1)} />
          </label>
        </div>
        {error && <p className="field-error availability-error" role="alert">{error}</p>}
        {slotContent}
      </section>

      {selectedSlot && <section className="availability-result" aria-live="polite">
        <span className="availability-result-icon" aria-hidden="true">✓</span>
        <div className="availability-result-content">
          <p className="eyebrow">GOOD NEWS</p>
          <h2>There is availability</h2>
          <p>Your party of {partySize} can be seated for {selectedSlot.start_time}–{selectedSlot.end_time}. {selectedSlot.remaining_seats} seats remain.</p>
          {selectedSlot.layout_summary && <p className="layout-summary"><strong>Seating preview:</strong> {selectedSlot.layout_summary}</p>}
          <Link className="submit-button availability-book" to={bookingPath} state={{ availabilitySearch: {
            date, partySize, slotId: selectedSlot.slot_id,
          } }}>{bookingPath === '/login' ? 'Sign in to book' : 'Book now'} <span aria-hidden="true">→</span></Link>
        </div>
      </section>}
      <p className="availability-footnote">Checking availability does not reserve seats. Complete a booking to secure your table.</p>
    </main>
  )
}

export default AvailabilityPage
