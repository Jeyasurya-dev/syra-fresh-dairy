/**
 * SYRA Fresh Hub Manager — API Client
 * Mirrors frontend/admin/js/admin-api.js but keeps the Hub Manager JWT
 * completely separate from the Admin/customer sessions (different
 * localStorage keys), so all three can be logged in on the same browser.
 */
const HM_API_BASE = window.SYRA_API_BASE || 'https://syra-fresh-backend.onrender.com/api';

const HubManagerApi = {
  token() {
    return localStorage.getItem('syra_hm_token');
  },

  async request(path, { method = 'GET', body, auth = true } = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (auth && this.token()) headers['Authorization'] = `Bearer ${this.token()}`;

    try {
      const res = await fetch(`${HM_API_BASE}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 401 && auth) {
        HubManagerAuth.logout();
      }
      if (!res.ok) {
        const message = data.message || Object.values(data.errors || {})[0] || 'Something went wrong';
        throw new HubManagerApiError(message, res.status, data.errors);
      }
      return data;
    } catch (err) {
      if (err instanceof HubManagerApiError) throw err;
      throw new HubManagerApiError('Could not reach SYRA Fresh servers. Check your connection.', 0);
    }
  },

  get(path) { return this.request(path, { method: 'GET' }); },
  post(path, body) { return this.request(path, { method: 'POST', body }); },
  put(path, body) { return this.request(path, { method: 'PUT', body }); },
  del(path) { return this.request(path, { method: 'DELETE' }); },
};

class HubManagerApiError extends Error {
  constructor(message, status, fieldErrors) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors || {};
  }
}

const HubManagerAuth = {
  isLoggedIn() { return !!localStorage.getItem('syra_hm_token'); },

  currentManager() {
    const raw = localStorage.getItem('syra_hm');
    return raw ? JSON.parse(raw) : null;
  },

  async login({ email, password }) {
    const data = await HubManagerApi.request('/hub-manager/auth/login', { method: 'POST', body: { email, password }, auth: false });
    localStorage.setItem('syra_hm_token', data.token);
    localStorage.setItem('syra_hm', JSON.stringify(data.hub_manager));
    return data.hub_manager;
  },

  logout() {
    localStorage.removeItem('syra_hm_token');
    localStorage.removeItem('syra_hm');
    window.location.href = '/hubmanager/login.html';
  },

  requireLogin() {
    if (!this.isLoggedIn()) {
      window.location.href = '/hubmanager/login.html';
      return false;
    }
    return true;
  },
};

function hmToast(message) {
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

function hmSlugifyStatus(status) {
  return (status || '').toString().toLowerCase().replace(/\s+/g, '-');
}
function hmStatusBadgeHTML(status) {
  return `<span class="badge-status st-${hmSlugifyStatus(status)}">${status}</span>`;
}
function hmFormatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}
function hmFormatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}
function hmEscapeHTML(str) {
  return (str || '').toString().replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
