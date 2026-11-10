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

function CustomerReservationHistoryPage() {
  const { session } = useAuth()
  const [reservations, setReservations] = useState([])
  const [loading, setLoading] = useState(true)
  const notify = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker') return undefined
    let active = true
    apiRequest(`/reservations?user_id=${encodeURIComponent(session.userProfile.id)}`, {
      headers: { Authorization: `Bearer ${session.token}` },
    }).then((response) => {
      if (active) setReservations(reservationsFrom(response))
    }).catch((error) => {
      if (active) notify(error.message || 'Could not load your booking history.')
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [session, notify])

  if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker') return <Navigate to="/login" replace />

  return (
    <main className="page">
      <button className="back-link" type="button" onClick={() => window.history.length > 1 ? navigate(-1) : navigate('/home/hiker')}>
        ← Back
      </button>
      <h1>Booking history</h1>
      {loading ? <p>Loading your bookings…</p> : reservations.length === 0 ? (
        <p>You don’t have any bookings yet. <Link to="/customer/book-table">Book a table</Link>.</p>
      ) : (
        <ul className="reservation-history-list">
          {reservations.map((reservation, index) => (
            <li key={reservation.reservation_id ?? reservation.reservationId ?? reservation.id ?? index}>
              <strong>{reservation.date ?? reservation.slot_date ?? reservation.slotDate ?? 'Booking'}</strong>
              <span>{reservation.start_time ?? reservation.startTime ?? reservation.time ?? ''}</span>
              <span>{reservation.party_size ?? reservation.partySize ?? reservation.guests ?? '—'} guests</span>
              <span>{reservation.booking_reference ?? reservation.bookingReference ?? ''}</span>
            </li>
          ))}
        </ul>
      )}
      <Link to="/customer/book-table">Book a table</Link>
    </main>
  )
}

export default CustomerReservationHistoryPage
