import { useEffect, useRef, useState } from 'react'
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
  const [isVisible, setIsVisible] = useState(true)

  useEffect(() => {
    let previousScrollY = window.scrollY
    const onScroll = () => {
      const currentScrollY = window.scrollY
      if (currentScrollY < 40 || currentScrollY < previousScrollY - 4) setIsVisible(true)
      else if (currentScrollY > previousScrollY + 4) setIsVisible(false)
      previousScrollY = currentScrollY
    }
    const onMouseMove = (event) => {
      if (event.clientY <= 12) setIsVisible(true)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('mousemove', onMouseMove)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('mousemove', onMouseMove)
    }
  }, [])

  if (!session?.isAuthenticated || ['/', '/login', '/register'].includes(location.pathname) || location.pathname.startsWith('/home/')) return null

  const role = session.userProfile.role
  const links = role === 'Hiker'
    ? [
        { label: 'Home', to: '/home/hiker' },
        { label: 'Availability', to: '/availability' },
        { label: 'Book a table', to: '/customer/book-table' },
        { label: 'Booking history', to: '/customer/reservations' },
      ]
    : [
        { label: 'Home', to: `/home/${role.toLowerCase()}` },
        { label: 'Times & tables', to: '/employee/slots' },
      ]

  function handleSignOut() {
    if (menuRef.current) menuRef.current.open = false
    signOut()
    void navigate('/login', { replace: true })
  }

  return (
    <header className={`site-nav${isVisible ? '' : ' site-nav-hidden'}`}>
      <nav className="site-nav-inner" aria-label="Main navigation">
        <Link className="site-nav-brand" to={`/home/${role.toLowerCase()}`} aria-label="MountainHut dashboard">
          <img src="/logo.png" alt="" />
        </Link>
        <div className="site-nav-links">
          {links.map((link) => (
            <Link
              className={location.pathname === link.to ? 'site-nav-link site-nav-link-active' : 'site-nav-link'}
              to={link.to}
              key={link.to}
            >
              {link.label}
            </Link>
          ))}
        </div>
        <details className="account-menu" ref={menuRef}>
          <summary className="account-avatar" aria-label="Open account menu">
            <span>{initialsForUser(session.userProfile)}</span>
          </summary>
          <div className="account-dropdown">
            <div className="account-identity">
              <strong>{session.userProfile.fullName || session.userProfile.email}</strong>
              <span>{role}</span>
            </div>
            <button className="account-signout" type="button" onClick={handleSignOut}>
              <span aria-hidden="true">↪</span> Sign out
            </button>
          </div>
        </details>
      </nav>
    </header>
  )
}

export default AccountMenu
