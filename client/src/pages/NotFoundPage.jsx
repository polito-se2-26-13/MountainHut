import { Link } from 'react-router'

function NotFoundPage() {
  return (
    <main className="page">
      <h1>Page not found</h1>
      <p>The page you are looking for does not exist or has been moved.</p>
      <Link to="/">Back to home</Link>
    </main>
  )
}

export default NotFoundPage
