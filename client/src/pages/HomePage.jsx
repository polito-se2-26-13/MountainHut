import { Link } from 'react-router'

function HomePage() {
  return (
    <main className="home-page">
      <section className="home-hero-copy" aria-labelledby="home-title">
        <p className="home-kicker">YOUR MOUNTAIN ESCAPE</p>
        <h1 id="home-title">MountainHut</h1>
        <p className="home-welcome">Welcome to the mountains.</p>
        <p className="home-description">Find a place to pause, explore, and gather.</p>
        <div className="home-actions">
          <Link to="/login">Sign in</Link>
          <Link to="/register">Create an account</Link>
        </div>
      </section>
    </main>
  )
}

export default HomePage
