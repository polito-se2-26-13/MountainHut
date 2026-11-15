import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router'
import { apiRequest } from '../api/api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import { useToast } from '../components/ToastProvider.jsx'

function reservationsFrom(response) {
  if (Array.isArray(response)) return response
  if (Array.isArray(response?.reservations)) return response.reservations
  if (Array.isArray(response?.items)) return response.items
  return []
}

function formatCreatedAt(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function newestFirst(reservations) {
  return [...reservations].sort((a, b) => {
    const timeA = Date.parse(a.created_at || '')
    const timeB = Date.parse(b.created_at || '')
    const validA = Number.isFinite(timeA)
    const validB = Number.isFinite(timeB)
    if (validA !== validB) return validA ? -1 : 1
    return validA ? timeB - timeA : 0
  })
}

function CustomerReservationHistoryPage() {
  const { session } = useAuth()
  const [reservations, setReservations] = useState([])
  const [loading, setLoading] = useState(true)
  const notify = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker') return undefined
    let active = true
    apiRequest(`/reservations/user`, {
      headers: { Authorization: `Bearer ${session.token}` },
    }).then((response) => {
      if (active) setReservations(newestFirst(reservationsFrom(response)))
    }).catch((error) => {
      if (!active) return
      if (error.status === 404) {
        setReservations([])
        return
      }
      notify(error.message || 'Could not load your booking history.')
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [session, notify])

  if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker') return <Navigate to="/login" replace />

  return (
    <main className="page reservation-history-page">
      <header className="reservation-history-header">
        <div>
          <button className="back-link" type="button" onClick={() => window.history.length > 1 ? navigate(-1) : navigate('/home/hiker')}>
            ← Back
          </button>
          <p className="eyebrow">MOUNTAINHUT · YOUR BOOKINGS</p>
          <h1>Booking history</h1>
          <p className="form-intro">Review your reservations and assigned seating.</p>
          <Link className="history-book-button" to="/customer/book-table">Book a table</Link>
        </div>
        <div className="booking-header-mark" aria-hidden="true">MH</div>
      </header>
      {loading ? <p>Loading your bookings…</p> : reservations.length === 0 ? (
        <p className="reservation-history-empty">You don’t have any bookings yet.</p>
      ) : (
        <ul className="reservation-history-list">
          {reservations.map((reservation, index) => (
            <li key={reservation.reservation_id ?? reservation.reservationId ?? reservation.id ?? index}>
              <strong>{reservation.booking_reference || 'Booking'}</strong>
              {reservation.date && <span>{reservation.date} · {reservation.start_time}–{reservation.end_time}</span>}
              <span>{reservation.party_size ?? '—'} guests · {reservation.status || 'Status unavailable'}</span>
              {reservation.created_at && <span>Created {formatCreatedAt(reservation.created_at)}</span>}
              {reservation.assigned_tables?.length > 0 && (
                <span>Tables: {reservation.assigned_tables.map((table) => `${table.table_number} (${table.assigned_seats} seats)`).join(', ')}</span>
              )}
              {reservation.special_requirements && <span>Requests: {reservation.special_requirements}</span>}
              {(reservation.contact_name || reservation.contact_email) && (
                <span>Contact: {[reservation.contact_name, reservation.contact_email, reservation.contact_phone].filter(Boolean).join(' · ')}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}

export default CustomerReservationHistoryPage
