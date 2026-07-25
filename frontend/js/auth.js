/**
 * SYRA Fresh — Auth Helpers
 * Session state lives in localStorage as a JWT; this module wraps
 * register/login/logout and keeps the header UI in sync.
 */
const Auth = {
  isLoggedIn() {
    return !!localStorage.getItem('syra_token');
  },

  currentUser() {
    const raw = localStorage.getItem('syra_user');
    return raw ? JSON.parse(raw) : null;
  },

  async register({ name, email, password, phone }) {
    const data = await Api.post('/auth/register', { name, email, password, phone });
    this._persist(data.token, data.user);
    return data.user;
  },

  async login({ email, password }) {
    const data = await Api.post('/auth/login', { email, password });
    this._persist(data.token, data.user);
    return data.user;
  },

  logout() {
    localStorage.removeItem('syra_token');
    localStorage.removeItem('syra_user');
    window.location.href = '/index.html';
  },

  _persist(token, user) {
    localStorage.setItem('syra_token', token);
    localStorage.setItem('syra_user', JSON.stringify(user));
  },

  requireLogin(redirectTo = '/pages/login.html') {
    if (!this.isLoggedIn()) {
      window.location.href = `${redirectTo}?next=${encodeURIComponent(window.location.pathname)}`;
      return false;
    }
    return true;
  },
};
