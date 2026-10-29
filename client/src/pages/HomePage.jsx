import { Link } from 'react-router'

function HomePage() {
  return (
    <main className="page">
      <h1>MountainHut</h1>
      <p>Welcome to MountainHut.</p>
      <div className="home-actions">
        <Link to="/login">Sign in</Link>
        <Link to="/register">Create an account</Link>
      </div>
    </main>
  )
}

export default HomePage
