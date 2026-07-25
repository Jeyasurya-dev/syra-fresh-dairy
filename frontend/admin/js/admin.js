/**
 * SYRA Fresh Admin — Shell (sidebar + topbar)
 * Every admin page (except login) has:
 *   <div class="admin-layout">
 *     <aside id="admin-sidebar"></aside>
 *     <div class="admin-content">
 *       <header id="admin-topbar"></header>
 *       <main class="admin-main">...page content...</main>
 *     </div>
 *   </div>
 * initAdminShell('products') fills in the sidebar/topbar, guards the route
 * behind AdminAuth, and wires up theme + mobile menu toggling.
 */

const ADMIN_NAV = [
  { key: 'dashboard', label: 'Dashboard', icon: '📊', href: '/admin/dashboard.html' },
  { key: 'products', label: 'Products', icon: '🛒', href: '/admin/products.html' },
  { key: 'categories', label: 'Categories', icon: '🗂️', href: '/admin/categories.html' },
  { key: 'inventory', label: 'Inventory', icon: '📦', href: '/admin/inventory.html' },
  { key: 'orders', label: 'Orders', icon: '🧾', href: '/admin/orders.html' },
  { key: 'assignments', label: 'Assignments', icon: '🚚', href: '/admin/assignments.html' },
  { key: 'districts', label: 'Districts', icon: '🗺️', href: '/admin/districts.html' },
  { key: 'hubs', label: 'Hubs', icon: '🏢', href: '/admin/hubs.html' },
  { key: 'hub-managers', label: 'Hub Managers', icon: '🧑‍💼', href: '/admin/hub-managers.html' },
  { key: 'delivery-boys', label: 'Delivery Boys', icon: '🛵', href: '/admin/delivery-boys.html' },
  { key: 'salary', label: 'Salary', icon: '💵', href: '/admin/salary.html' },
  { key: 'customers', label: 'Customers', icon: '👥', href: '/admin/customers.html' },
  { key: 'coupons', label: 'Coupons', icon: '🏷️', href: '/admin/coupons.html' },
  { key: 'reviews', label: 'Reviews', icon: '⭐', href: '/admin/reviews.html' },
  { key: 'reports', label: 'Sales Reports', icon: '📈', href: '/admin/reports.html' },
  { key: 'notifications', label: 'Notifications', icon: '🔔', href: '/admin/notifications.html' },
  { key: 'contact-messages', label: 'Contact Messages', icon: '📩', href: '/admin/contact-messages.html' },
  { key: 'career-applications', label: 'Career Applications', icon: '📄', href: '/admin/career-applications.html' },
  { key: 'settings', label: 'Settings', icon: '⚙️', href: '/admin/settings.html' },
];

function adminSidebarHTML(active) {
  return `
    <div class="admin-logo">
      <img src="/assets/Logo.png" alt="SYRA Fresh Logo" class="admin-logo-img">
      <span>SYRA Admin</span>
    </div>
    <nav class="admin-nav">
      <div class="nav-section-label">Main</div>
      ${ADMIN_NAV.map((item) => `
        <a href="${item.href}" class="${item.key === active ? 'active' : ''}">
          <span class="ic">${item.icon}</span> ${item.label}
        </a>`).join('')}
    </nav>
    <div class="admin-sidebar-footer">
      <a href="/index.html" target="_blank"><span class="ic">🌐</span> View Storefront</a>
      <a href="#" onclick="AdminAuth.logout(); return false;"><span class="ic">🚪</span> Log Out</a>
    </div>`;
}

function adminTopbarHTML(title) {
  const admin = AdminAuth.currentAdmin() || { name: 'Admin' };
  const initials = (admin.name || 'A').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();
  return `
    <button class="mobile-menu-btn" id="admin-mobile-toggle">☰</button>
    <h1>${title}</h1>
    <div class="spacer"></div>
    <button class="theme-toggle" onclick="toggleAdminTheme()" aria-label="Toggle dark mode">
      <svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>
      <svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>
    </button>
    <div class="admin-avatar" title="${admin.name}">${initials}</div>`;
}

function toggleAdminTheme() {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('syra_theme', next);
}

const PAGE_TITLES = {
  dashboard: 'Dashboard', products: 'Products', categories: 'Categories', inventory: 'Inventory',
  orders: 'Orders', customers: 'Customers', coupons: 'Coupons', reviews: 'Reviews',
  reports: 'Sales Reports', settings: 'Settings',
  // BUG FIX: these three pages exist in ADMIN_NAV and are fully functional,
  // but had no entry here, so their topbar heading silently fell back to
  // the generic "Admin" instead of a real page title.
  assignments: 'Delivery Assignments', 'delivery-boys': 'Delivery Boys', notifications: 'Notifications',
  districts: 'District Management', hubs: 'Hub Management', 'hub-managers': 'Hub Manager Management',
  salary: 'Salary Management',
  'contact-messages': 'Contact Messages', 'career-applications': 'Career Applications',
};

function initAdminShell(activeKey) {
  if (!AdminAuth.requireLogin()) return false;

  document.documentElement.setAttribute('data-theme', localStorage.getItem('syra_theme') || 'light');

  const sidebar = document.getElementById('admin-sidebar');
  const topbar = document.getElementById('admin-topbar');
  if (sidebar) { sidebar.className = 'admin-sidebar'; sidebar.innerHTML = adminSidebarHTML(activeKey); }
  if (topbar) { topbar.className = 'admin-topbar'; topbar.innerHTML = adminTopbarHTML(PAGE_TITLES[activeKey] || 'Admin'); }

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

// ---------- Small shared UI helpers used across admin pages ----------
function openModal(id) { document.getElementById(id).classList.add('show'); }
function closeModal(id) { document.getElementById(id).classList.remove('show'); }

function renderAdminPagination(elId, pagination, onPage) {
  const el = document.getElementById(elId);
  if (!el) return;
  const totalPages = Math.max(1, Math.ceil(pagination.total / pagination.page_size));
  let html = '';
  for (let i = 1; i <= totalPages; i++) {
    html += `<button class="btn btn-sm ${i === pagination.page ? 'btn-primary' : 'btn-outline'}" data-page="${i}">${i}</button>`;
  }
  el.innerHTML = html;
  el.querySelectorAll('button').forEach((btn) => btn.addEventListener('click', () => onPage(+btn.dataset.page)));
}

function escapeHTML(str) {
  return (str || '').toString().replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
