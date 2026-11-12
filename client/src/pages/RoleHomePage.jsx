import { Link, Navigate, useParams } from 'react-router'
import { useAuth } from '../auth/AuthContext.jsx'

const roleByPath = {
  hiker: 'Hiker',
  employee: 'Employee',
  warden: 'Warden',
}

const roleHomeContent = {
  Hiker: {
    image: '/DSC00187.JPG',
    kicker: 'YOUR MOUNTAIN ESCAPE',
    title: 'Make room for a slower moment.',
    description: 'Plan a table at the hut or revisit the details of a past booking.',
    actions: [
      { title: 'Book a table', description: 'Choose a date and service time for your group.', to: '/customer/book-table', icon: '↗' },
      { title: 'Booking history', description: 'Review your previous reservations.', to: '/customer/reservations', icon: '⌁' },
    ],
  },
  Employee: {
    image: '/DSC00260.JPG',
    kicker: 'MOUNTAINHUT · TEAM',
    title: 'Prepare the day on the mountain.',
    description: 'Set up service times and table capacity for upcoming guests.',
    actions: [
      { title: 'Times & tables', description: 'Configure service slots and table layouts.', to: '/employee/slots', icon: '＋' },
    ],
  },
  Warden: {
    image: '/DSC00277.JPG',
    kicker: 'MOUNTAINHUT · MANAGEMENT',
    title: 'Welcome to your workspace.',
    description: 'A clear starting point for your MountainHut sessions.',
    actions: [
      { title: 'Times & tables', description: 'Configure service slots and table layouts.', to: '/employee/slots', icon: '＋' },
      { title: 'MountainHut home', description: 'Visit the public MountainHut landing page.', to: '/', icon: '↗' },
    ],
  },
}

function RoleHomePage() {
  const { role: pathRole } = useParams()
  const { session } = useAuth()
  const role = roleByPath[pathRole]

  if (!role) return <Navigate to="/404" replace />
  if (!session?.isAuthenticated || session.userProfile.role !== role) {
    return <Navigate to="/login" replace />
  }

  const content = roleHomeContent[role]

  return (
    <main className={`role-home-page role-home-${pathRole}`} style={{ '--role-home-image': `url("${content.image}")` }}>
      <section className="role-home-content" aria-labelledby="role-home-title">
        <p className="role-home-kicker">{content.kicker}</p>
        <p className="role-home-greeting">Welcome back, {session.userProfile.fullName || session.userProfile.email}</p>
        <h1 id="role-home-title">{content.title}</h1>
        <p className="role-home-description">{content.description}</p>
        <nav className="role-home-actions" aria-label={`${role} actions`}>
          {content.actions.map((action) => (
            <Link className="role-home-card" to={action.to} key={action.title}>
              <span className="role-home-card-icon" aria-hidden="true">{action.icon}</span>
              <span className="role-home-card-copy">
                <strong>{action.title}</strong>
                <span>{action.description}</span>
              </span>
              <span className="role-home-card-arrow" aria-hidden="true">→</span>
            </Link>
          ))}
        </nav>
        <p className="role-home-role">Signed in as {role}</p>
      </section>
    </main>
  )
}

export default RoleHomePage
