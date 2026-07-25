/**
 * SYRA Fresh Hub Manager — Shell (sidebar + topbar)
 * Same layout convention as the Admin panel (frontend/admin/js/admin.js):
 *   <div class="admin-layout">
 *     <aside id="admin-sidebar"></aside>
 *     <div class="admin-content">
 *       <header id="admin-topbar"></header>
 *       <main class="admin-main">...page content...</main>
 *     </div>
 *   </div>
 * initHubManagerShell('orders') fills in the sidebar/topbar and guards the
 * route behind HubManagerAuth - a Hub Manager only ever sees their own hub's
 * data (enforced server-side too, on every route in hub_manager_routes.py).
 */

const HM_NAV = [
  { key: 'dashboard', label: 'Dashboard', icon: '📊', href: '/hubmanager/dashboard.html' },
  { key: 'orders', label: 'Orders', icon: '🧾', href: '/hubmanager/orders.html' },
  { key: 'delivery-boys', label: 'Delivery Boys', icon: '🛵', href: '/hubmanager/delivery-boys.html' },
  { key: 'customers', label: 'Customers', icon: '👥', href: '/hubmanager/customers.html' },
  { key: 'inventory', label: 'Stock', icon: '📦', href: '/hubmanager/inventory.html' },
  { key: 'attendance', label: 'Attendance', icon: '🗓️', href: '/hubmanager/attendance.html' },
  { key: 'reports', label: 'Reports', icon: '📈', href: '/hubmanager/reports.html' },
  { key: 'salary', label: 'My Salary', icon: '🧾', href: '/hubmanager/salary.html' },
  { key: 'settings', label: 'Settings', icon: '⚙️', href: '/hubmanager/settings.html' },
];

function hmSidebarHTML(active) {
  const manager = HubManagerAuth.currentManager() || {};
  return `
    <div class="admin-logo">
      <img src="/assets/Logo.png" alt="SYRA Fresh Logo" class="admin-logo-img">
      <span>${manager.hub_name || 'Hub Manager'}</span>
    </div>
    <nav class="admin-nav">
      <div class="nav-section-label">Main</div>
      ${HM_NAV.map((item) => `
        <a href="${item.href}" class="${item.key === active ? 'active' : ''}">
          <span class="ic">${item.icon}</span> ${item.label}
        </a>`).join('')}
    </nav>
    <div class="admin-sidebar-footer">
      <a href="#" onclick="HubManagerAuth.logout(); return false;"><span class="ic">🚪</span> Log Out</a>
    </div>`;
}

function hmTopbarHTML(title) {
  const manager = HubManagerAuth.currentManager() || { name: 'Hub Manager' };
  const initials = (manager.name || 'H').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();
  return `
    <button class="mobile-menu-btn" id="admin-mobile-toggle">☰</button>
    <h1>${title}</h1>
    <div class="spacer"></div>
    <button class="theme-toggle" onclick="toggleHmTheme()" aria-label="Toggle dark mode">
      <svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>
      <svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>
    </button>
    <div class="admin-avatar" title="${manager.name} — ${manager.hub_name || ''}">${initials}</div>`;
}

function toggleHmTheme() {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('syra_theme', next);
}

const HM_PAGE_TITLES = {
  dashboard: 'Hub Dashboard', orders: 'Orders', 'delivery-boys': 'Delivery Boys',
  customers: 'Customers', inventory: 'Stock (Read-only)', attendance: 'Attendance',
  reports: 'Reports', settings: 'Settings',
  salary: 'My Salary',
};

function initHubManagerShell(activeKey) {
  if (!HubManagerAuth.requireLogin()) return false;

  document.documentElement.setAttribute('data-theme', localStorage.getItem('syra_theme') || 'light');

  const sidebar = document.getElementById('admin-sidebar');
  const topbar = document.getElementById('admin-topbar');
  if (sidebar) { sidebar.className = 'admin-sidebar'; sidebar.innerHTML = hmSidebarHTML(activeKey); }
  if (topbar) { topbar.className = 'admin-topbar'; topbar.innerHTML = hmTopbarHTML(HM_PAGE_TITLES[activeKey] || 'Hub Manager'); }

  const mobileToggle = document.getElementById('admin-mobile-toggle');
  if (mobileToggle) {
    mobileToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  }
  document.addEventListener('click', (e) => {
    if (sidebar && sidebar.classList.contains('open') && !sidebar.contains(e.target) && e.target !== mobileToggle) {
      sidebar.classList.remove('open');
    }
  });

  return true;
}

function hmOpenModal(id) { document.getElementById(id).classList.add('show'); }
function hmCloseModal(id) { document.getElementById(id).classList.remove('show'); }
