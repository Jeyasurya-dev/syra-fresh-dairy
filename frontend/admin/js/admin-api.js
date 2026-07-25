/**
 * SYRA Fresh Admin — API Client
 * Mirrors frontend/js/api.js but keeps the admin JWT completely separate
 * from the customer session (different localStorage keys), so a person can
 * be logged into the storefront and the admin panel in the same browser.
 */
const ADMIN_API_BASE = window.SYRA_API_BASE || 'https://syra-fresh-backend.onrender.com/api';

const AdminApi = {
  token() {
    return localStorage.getItem('syra_admin_token');
  },

  async request(path, { method = 'GET', body, auth = true, isForm = false } = {}) {
    const headers = {};
    if (!isForm) headers['Content-Type'] = 'application/json';
    if (auth && this.token()) headers['Authorization'] = `Bearer ${this.token()}`;

    try {
      const res = await fetch(`${ADMIN_API_BASE}${path}`, {
        method,
        headers,
        body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 401 && auth) {
        AdminAuth.logout();
      }
      if (!res.ok) {
        const message = data.message || Object.values(data.errors || {})[0] || 'Something went wrong';
        throw new AdminApiError(message, res.status, data.errors);
      }
      return data;
    } catch (err) {
      if (err instanceof AdminApiError) throw err;
      throw new AdminApiError('Could not reach SYRA Fresh servers. Check your connection.', 0);
    }
  },

  get(path) { return this.request(path, { method: 'GET' }); },
  post(path, body) { return this.request(path, { method: 'POST', body }); },
  put(path, body) { return this.request(path, { method: 'PUT', body }); },
  del(path) { return this.request(path, { method: 'DELETE' }); },
  upload(path, formData) { return this.request(path, { method: 'POST', body: formData, isForm: true }); },
};

class AdminApiError extends Error {
  constructor(message, status, fieldErrors) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors || {};
  }
}

const AdminAuth = {
  isLoggedIn() { return !!localStorage.getItem('syra_admin_token'); },

  currentAdmin() {
    const raw = localStorage.getItem('syra_admin');
    return raw ? JSON.parse(raw) : null;
  },

  async login({ email, password }) {
    const data = await AdminApi.request('/admin/login', { method: 'POST', body: { email, password }, auth: false });
    localStorage.setItem('syra_admin_token', data.token);
    localStorage.setItem('syra_admin', JSON.stringify(data.admin));
    return data.admin;
  },

  logout() {
    localStorage.removeItem('syra_admin_token');
    localStorage.removeItem('syra_admin');
    window.location.href = '/admin/login.html';
  },

  requireLogin() {
    if (!this.isLoggedIn()) {
      window.location.href = '/admin/login.html';
      return false;
    }
    return true;
  },
};

function resolveAdminImage(path) {
  if (!path) return 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&q=80';
  if (path.startsWith('http')) return path;
  // BUG FIX: delivery boy document uploads used to be saved as bare relative
  // paths (e.g. "aadhaar/xxx.jpg") instead of "/static/uploads/aadhaar/xxx.jpg".
  // The backend now always returns the correct absolute-from-root path for
  // new uploads, but this keeps any already-saved legacy records working too.
  const normalized = path.startsWith('/') ? path : `/static/uploads/${path}`;
  return `${ADMIN_API_BASE.replace('/api', '')}${normalized}`;
}

function adminToast(message) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('show'), 2600);
}

function slugifyStatus(status) {
  return (status || '').toString().toLowerCase().replace(/\s+/g, '-');
}
function statusBadgeHTML(status) {
  return `<span class="badge-status st-${slugifyStatus(status)}">${status}</span>`;
}
function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}
function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}
function debounce(fn, wait = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
}
