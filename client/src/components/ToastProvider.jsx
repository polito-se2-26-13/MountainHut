/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useState } from 'react'

const ToastContext = createContext(null)
let nextToastId = 0

function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const notify = useCallback((message, type = 'error') => {
    const id = ++nextToastId
    setToasts((current) => [...current, { id, message, type }])
    window.setTimeout(() => dismissToast(id), 4500)
  }, [dismissToast])

  const value = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region" aria-label="Notifications">
        {toasts.map((toast) => (
          <div
            className={`toast toast-${toast.type}`}
            key={toast.id}
            role={toast.type === 'error' ? 'alert' : 'status'}
            aria-live={toast.type === 'error' ? 'assertive' : 'polite'}
          >
            <span className="toast-icon" aria-hidden="true">{toast.type === 'error' ? '!' : '✓'}</span>
            <span className="toast-message">{toast.message}</span>
            <button className="toast-dismiss" type="button" onClick={() => dismissToast(toast.id)} aria-label="Dismiss notification">×</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context.notify
}

export default ToastProvider
