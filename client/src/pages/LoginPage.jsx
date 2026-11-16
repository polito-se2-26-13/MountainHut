import { useState } from 'react'
import { Button, Form, Input } from 'antd'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '../auth/AuthContext.jsx'
import { useToast } from '../components/ToastProvider.jsx'
import { apiRequest } from '../api/api.js'

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function routeForRole(role) {
  return {
    Hiker: '/home/hiker',
    Employee: '/home/employee',
    Warden: '/home/warden',
  }[role]
}

function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [touched, setTouched] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const { signIn } = useAuth()
  const notify = useToast()
  const navigate = useNavigate()

  const emailError = !username.trim()
    ? 'Email is required.'
    : !emailPattern.test(username.trim())
      ? 'Please enter a valid email address.'
      : ''
  const passwordError = password ? '' : 'Password is required.'
  const showEmailError = touched.username || submitted ? emailError : ''
  const showPasswordError = touched.password || submitted ? passwordError : ''

  async function handleSubmit() {
    setSubmitted(true)
    setTouched({ username: true, password: true })
    setFieldErrors({})
    if (emailError || passwordError) return

    setLoading(true)
    try {
      const result = await apiRequest('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      })

      if (!result?.token || !result?.user) {
        throw new Error('The server returned an invalid login response.')
      }

      const destination = routeForRole(result.user.role)
      if (!destination) {
        throw new Error('Your account role is not supported by this application.')
      }
      signIn(result.token, result.user)
      navigate(destination, { replace: true })
    } catch (error) {
      setFieldErrors(error.fieldErrors || {})
      notify(error.message || 'Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  function updateField(field, value) {
    if (field === 'username') setUsername(value)
    if (field === 'password') setPassword(value)
    setTouched((current) => ({ ...current, [field]: true }))
    setFieldErrors((current) => ({ ...current, [field]: '' }))
  }

  return (
    <main className="page register-page">
      <section className="register-card login-card" aria-labelledby="login-title">
        <Link className="back-link" to="/">MountainHut</Link>
        <h1 id="login-title">Welcome back</h1>
        <p className="form-intro">Sign in with your email and password.</p>

        <Form className="mh-form" onFinish={handleSubmit} noValidate>
          <div className="login-fields">
            <label className="form-field">
              <span>Email <span className="required-mark" aria-hidden="true">*</span></span>
              <Input
                className="mh-control"
                name="username"
                type="email"
                required
                autoComplete="username"
                value={username}
                onChange={(event) => updateField('username', event.target.value)}
                onBlur={() => setTouched((current) => ({ ...current, username: true }))}
                aria-invalid={Boolean(showEmailError || fieldErrors.username)}
                aria-describedby={showEmailError || fieldErrors.username ? 'login-email-error' : undefined}
              />
              {(showEmailError || fieldErrors.username) && <small className="field-error" id="login-email-error">{fieldErrors.username || showEmailError}</small>}
            </label>

            <label className="form-field">
              <span>Password <span className="required-mark" aria-hidden="true">*</span></span>
              <Input.Password
                className="mh-control"
                name="password"
                required
                autoComplete="current-password"
                visibilityToggle={false}
                value={password}
                onChange={(event) => updateField('password', event.target.value)}
                onBlur={() => setTouched((current) => ({ ...current, password: true }))}
                aria-invalid={Boolean(showPasswordError || fieldErrors.password)}
                aria-describedby={showPasswordError || fieldErrors.password ? 'login-password-error' : undefined}
              />
              {(showPasswordError || fieldErrors.password) && <small className="field-error" id="login-password-error">{fieldErrors.password || showPasswordError}</small>}
            </label>
          </div>

          <Button className="submit-button" type="primary" htmlType="submit" loading={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
          <p className="login-register-link">New to MountainHut? <Link to="/register">Create an account</Link></p>
          <p className="required-note"><span className="required-mark">*</span> Required fields</p>
        </Form>
      </section>
    </main>
  )
}

export default LoginPage
