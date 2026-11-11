import { useRef } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../auth/AuthContext.jsx'

function initialsForUser(user) {
  const name = user?.fullName?.trim()
  if (name) {
    return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  }
  return user?.email?.[0]?.toUpperCase() || 'U'
}

function AccountMenu() {
  const { session, signOut } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const menuRef = useRef(null)

  if (!session?.isAuthenticated || ['/login', '/register'].includes(location.pathname)) return null

  function handleSignOut() {
    if (menuRef.current) menuRef.current.open = false
    signOut()
    navigate('/login', { replace: true })
  }

  return (
    <div className="account-menu-position">
      <details className="account-menu" ref={menuRef}>
        <summary className="account-avatar" aria-label="Open account menu">
          <span>{initialsForUser(session.userProfile)}</span>
        </summary>
        <div className="account-dropdown">
          <div className="account-identity">
            <strong>{session.userProfile.fullName || session.userProfile.email}</strong>
            <span>{session.userProfile.role}</span>
          </div>
          {session.userProfile.role === 'Hiker' && (
            <Link className="account-menu-link" to="/customer/reservations" onClick={() => { if (menuRef.current) menuRef.current.open = false }}>
              <span aria-hidden="true">▤</span> Booking history
            </Link>
          )}
          <button className="account-signout" type="button" onClick={handleSignOut}>
            <span aria-hidden="true">↪</span> Sign out
          </button>
        </div>
      </details>
    </div>
  )
}

export default AccountMenu
