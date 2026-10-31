import { Link, Navigate, useParams } from 'react-router'
import { useAuth } from '../auth/AuthContext.jsx'

const roleByPath = {
  hiker: 'Hiker',
  employee: 'Employee',
  manager: 'Manager',
}

function RoleHomePage() {
  const { role: pathRole } = useParams()
  const { session } = useAuth()
  const role = roleByPath[pathRole]

  if (!role) return <Navigate to="/404" replace />
  if (!session?.isAuthenticated || session.userProfile.role !== role) {
    return <Navigate to="/login" replace />
  }

  return (
    <main className="page">
      <h1>{role} home</h1>
      <p>Welcome, {session.userProfile.fullName || session.userProfile.email}.</p>
      <p>You are signed in as a {role}.</p>
      {role === 'Employee' && <Link to="/employee/slots">Configure service slots and tables</Link>}
      <Link to="/">Back to the MountainHut home page</Link>
    </main>
  )
}

export default RoleHomePage
