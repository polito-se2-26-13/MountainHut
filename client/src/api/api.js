import { forgetStoredSession } from '../auth/AuthContext.jsx';

// Keep requests same-origin so the Vite proxy can forward them to the backend.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export async function apiRequest(path, options = {}) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const response = await fetch(`${API_BASE_URL}${normalizedPath}`, options);
  // the login sent with the request expired or is no longer valid: sign out and go back to the login page
  if (response.status === 401 && options.headers?.Authorization) {
    forgetStoredSession();
    window.location.assign('/login');
  }
  const responseText = await response.text();
  let data = null;

  if (responseText) {
    try {
      data = JSON.parse(responseText);
    } catch {
      data = responseText;
    }
  }

  if (!response.ok) {
    const detail = data?.detail
    const message = data?.message || (typeof detail === 'string' ? detail : null)
      || (Array.isArray(detail) ? detail.map((item) => item.msg).join(', ') : null)
      || `Request failed (${response.status})`
    const error = new Error(message)
    if (Array.isArray(detail)) {
      error.fieldErrors = Object.fromEntries(
        detail
          .filter((item) => Array.isArray(item.loc) && item.loc.length)
          .map((item) => [item.loc.at(-1), item.msg]),
      )
    }
    throw error
  }

  return data;
}

export default API_BASE_URL;

