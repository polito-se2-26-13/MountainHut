import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { apiRequest } from '../api/api.js'
import { useToast } from '../components/ToastProvider.jsx'

const initialValues = {
  email: '',
  password: '',
  confirmPassword: '',
  firstName: '',
  lastName: '',
  phone: '',
}

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const phonePattern = /^\+?[0-9][0-9\s().-]{6,19}$/

function validateField(name, values) {
  const value = values[name]

  if (name !== 'phone' && !value.trim()) return 'This field is required.'
  if (name === 'email' && value && !emailPattern.test(value.trim())) return 'Enter a valid email address.'
  if (name === 'password' && value && value.length < 8) return 'Password must be at least 8 characters.'
  if (name === 'confirmPassword' && value !== values.password) return 'Passwords do not match.'
  if (name === 'phone' && value && !phonePattern.test(value.trim())) return 'Enter a valid phone number.'
  return ''
}

function RegisterPage() {
  const [values, setValues] = useState(initialValues)
  const [touched, setTouched] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const notify = useToast()
  const loginButtonRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (success) loginButtonRef.current?.focus()
  }, [success])

  const errors = Object.fromEntries(
    Object.keys(initialValues).map((name) => [name, validateField(name, values)]),
  )
  const showError = (name) => (touched[name] || submitted ? errors[name] : '')

  function handleChange(event) {
    const { name, value } = event.target
    setValues((current) => ({ ...current, [name]: value }))
    setTouched((current) => ({
      ...current,
      [name]: true,
      ...(name === 'password' && values.confirmPassword ? { confirmPassword: true } : {}),
    }))
    setSuccess('')
  }

  function handleBlur(event) {
    setTouched((current) => ({ ...current, [event.target.name]: true }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitted(true)
    setTouched(Object.fromEntries(Object.keys(initialValues).map((name) => [name, true])))

    if (Object.values(errors).some(Boolean)) return

    setLoading(true)
    try {
      const payload = {
        email: values.email.trim(),
        password: values.password,
        firstName: values.firstName.trim(),
        lastName: values.lastName.trim(),
        ...(values.phone.trim() ? { phone: values.phone.trim() } : {}),
        role: 'Hiker',
      }
      const result = await apiRequest('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      setSuccess(result?.message || 'Registration successful.')
      setValues(initialValues)
      setTouched({})
      setSubmitted(false)
    } catch (error) {
      notify(error.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page register-page">
      <section className="register-card" aria-labelledby="register-title">
        <Link className="back-link" to="/">MountainHut</Link>
        <h1 id="register-title">Create your account</h1>
        <p className="form-intro">Join the MountainHut community.</p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-grid">
            <label className="form-field">
              <span>First name <span className="required-mark" aria-hidden="true">*</span></span>
              <input name="firstName" required autoComplete="given-name" value={values.firstName} onChange={handleChange} onBlur={handleBlur} aria-invalid={Boolean(showError('firstName'))} />
              {showError('firstName') && <small className="field-error">{showError('firstName')}</small>}
            </label>

            <label className="form-field">
              <span>Last name <span className="required-mark" aria-hidden="true">*</span></span>
              <input name="lastName" required autoComplete="family-name" value={values.lastName} onChange={handleChange} onBlur={handleBlur} aria-invalid={Boolean(showError('lastName'))} />
              {showError('lastName') && <small className="field-error">{showError('lastName')}</small>}
            </label>

            <label className="form-field form-field-wide">
              <span>Email <span className="required-mark" aria-hidden="true">*</span></span>
              <input name="email" type="email" required autoComplete="email" value={values.email} onChange={handleChange} onBlur={handleBlur} aria-invalid={Boolean(showError('email'))} />
              {showError('email') && <small className="field-error">{showError('email')}</small>}
            </label>

            <label className="form-field">
              <span>Password <span className="required-mark" aria-hidden="true">*</span></span>
              <input name="password" type="password" required autoComplete="new-password" value={values.password} onChange={handleChange} onBlur={handleBlur} aria-invalid={Boolean(showError('password'))} />
              <small className={showError('password') ? 'field-error' : 'field-hint'}>{showError('password') || 'Use at least 8 characters.'}</small>
            </label>

            <label className="form-field">
              <span>Confirm password <span className="required-mark" aria-hidden="true">*</span></span>
              <input name="confirmPassword" type="password" required autoComplete="new-password" value={values.confirmPassword} onChange={handleChange} onBlur={handleBlur} aria-invalid={Boolean(showError('confirmPassword'))} />
              {showError('confirmPassword') && <small className="field-error">{showError('confirmPassword')}</small>}
            </label>

            <label className="form-field form-field-wide">
              <span>Phone <span className="optional-mark">(optional)</span></span>
              <input name="phone" type="tel" autoComplete="tel" value={values.phone} onChange={handleChange} onBlur={handleBlur} aria-invalid={Boolean(showError('phone'))} />
              {showError('phone') && <small className="field-error">{showError('phone')}</small>}
            </label>

          </div>

          <button className="submit-button" type="submit" disabled={loading}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
          <p className="required-note"><span className="required-mark">*</span> Required fields</p>
        </form>
      </section>
      {success && (
        <div className="success-modal-backdrop">
          <section
            className="success-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="registration-success-title"
            aria-describedby="registration-success-message"
          >
            <div className="success-modal-icon" aria-hidden="true">✓</div>
            <p className="eyebrow">ACCOUNT READY</p>
            <h2 id="registration-success-title">Registration successful</h2>
            <p id="registration-success-message">{success} You can now sign in to your account.</p>
            <button
              className="submit-button"
              type="button"
              ref={loginButtonRef}
              onClick={() => navigate('/login', { replace: true })}
            >
              Return to sign in
            </button>
          </section>
        </div>
      )}
    </main>
  )
}

export default RegisterPage
