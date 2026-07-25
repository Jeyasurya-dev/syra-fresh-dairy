/**
 * SYRA Fresh — API Client
 * Thin wrapper around fetch() that talks to the Flask backend, attaches the
 * auth token automatically, and normalizes error handling.
 */
const API_BASE_URL = window.SYRA_API_BASE || 'http://localhost:5000/api';

const Api = {
  token() {
    return localStorage.getItem('syra_token');
  },

  async request(path, { method = 'GET', body, auth = false, isForm = false } = {}) {
    const headers = {};
    if (!isForm) headers['Content-Type'] = 'application/json';
    if (auth && this.token()) headers['Authorization'] = `Bearer ${this.token()}`;

    try {
      const res = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers,
        body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const message = data.message || Object.values(data.errors || {})[0] || 'Something went wrong';
        throw new ApiError(message, res.status, data.errors);
      }
      return data;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('Could not reach SYRA Fresh servers. Check your connection.', 0);
    }
  },

  get(path, auth = false) { return this.request(path, { method: 'GET', auth }); },
  post(path, body, auth = false) { return this.request(path, { method: 'POST', body, auth }); },
  put(path, body, auth = false) { return this.request(path, { method: 'PUT', body, auth }); },
  del(path, auth = false) { return this.request(path, { method: 'DELETE', auth }); },
};

class ApiError extends Error {
  constructor(message, status, fieldErrors) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors || {};
  }
}

// ---- Product image helper: resolves relative /static paths against the API host ----
function resolveImage(path) {
  if (!path) return 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&q=80';
  if (path.startsWith('http')) return path;
  return `${API_BASE_URL.replace('/api', '')}${path}`;
}
