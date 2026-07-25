/**
 * SYRA Fresh — Shared site header & footer
 * Injected into pages that include <div id="site-header-root"></div> and
 * <div id="site-footer-root"></div>. Keeps nav/footer identical across every
 * inner page without duplicating ~120 lines of markup per file.
 */

const NAV_LINKS = [
  { label: 'Home', href: '/index.html', key: 'home' },
  { label: 'Products', href: '/pages/shop.html', key: 'products' },
  { label: 'Categories', href: '/pages/categories.html', key: 'categories' },
  { label: 'Dairy Products', href: '/pages/shop.html?category=dairy-products', key: 'dairy' },
  { label: 'Ice Cream', href: '/pages/shop.html?category=ice-cream', key: 'icecream' },
  { label: 'Healthy Snacks', href: '/pages/shop.html?category=healthy-snacks', key: 'snacks' },
  { label: 'Fresh Fruits', href: '/pages/shop.html?category=fresh-fruits', key: 'fruits' },
  { label: 'About', href: '/pages/about.html', key: 'about' },
  { label: 'Contact', href: '/pages/contact.html', key: 'contact' },
];

function headerHTML(active) {
  return `
<header class="site-header">
  <div class="container header-top">
    <a href="/index.html" class="logo"><span class="dot"></span> SYRA Fresh</a>

    <form id="search-form" class="search-bar" role="search">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="text" id="search-input" placeholder="Search milk, paneer, mangoes...">
    </form>

    <div class="header-actions">
      <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle dark mode">
        <svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>
        <svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>
      </button>
      <a href="/pages/search.html" class="icon-btn" title="Search">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        Search
      </a>
      <a href="/pages/wishlist.html" class="icon-btn">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>
        Wishlist
      </a>
      <a href="/pages/cart.html" class="icon-btn">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6"/></svg>
        Cart
        <span class="badge-count cart-badge" style="display:none">0</span>
      </a>
      <a href="/pages/login.html" id="account-link" class="icon-btn">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        Account
      </a>
      <button id="mobile-nav-toggle" class="icon-btn" style="display:none">☰</button>
    </div>
  </div>
  <nav class="main-nav">
    <div class="container">
      <ul>
        ${NAV_LINKS.map((l) => `<li><a href="${l.href}" class="${l.key === active ? 'active' : ''}">${l.label}</a></li>`).join('')}
      </ul>
    </div>
  </nav>
</header>`;
}

function footerHTML() {
  const year = new Date().getFullYear();
  return `
<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div>
        <div class="footer-logo">SYRA Fresh</div>
        <p>Farm-fresh dairy, ice cream, healthy snacks and fruit — delivered daily across your city.</p>
        <div class="footer-social">
          <a href="#" aria-label="Instagram">IG</a>
          <a href="#" aria-label="Facebook">FB</a>
          <a href="#" aria-label="Twitter">X</a>
        </div>
      </div>
      <div>
        <h4>Shop</h4>
        <ul>
          <li><a href="/pages/shop.html?category=dairy-products">Dairy Products</a></li>
          <li><a href="/pages/shop.html?category=ice-cream">Ice Cream</a></li>
          <li><a href="/pages/shop.html?category=healthy-snacks">Healthy Snacks</a></li>
          <li><a href="/pages/shop.html?category=fresh-fruits">Fresh Fruits</a></li>
          <li><a href="/pages/categories.html">All Categories</a></li>
        </ul>
      </div>
      <div>
        <h4>Company</h4>
        <ul>
          <li><a href="/pages/about.html">About Us</a></li>
          <li><a href="/pages/contact.html">Contact</a></li>
          <li><a href="/pages/profile.html">My Account</a></li>
          <li><a href="/pages/orders.html">My Orders</a></li>
          <li><a href="/pages/wishlist.html">Wishlist</a></li>
        </ul>
      </div>
      <div>
        <h4>Support</h4>
        <ul>
          <li><a href="/pages/faq.html">FAQs</a></li>
          <li><a href="/pages/faq.html#shipping">Shipping Policy</a></li>
          <li><a href="/pages/faq.html#returns">Returns & Refunds</a></li>
          <li><a href="/pages/privacy.html">Privacy Policy</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <span>© ${year} SYRA Fresh. All rights reserved.</span>
      <span>Made with 🌿 for fresh living.</span>
    </div>
  </div>
</footer>`;
}

function initLayout(activeNav) {
  const headerRoot = document.getElementById('site-header-root');
  const footerRoot = document.getElementById('site-footer-root');
  if (headerRoot) headerRoot.outerHTML = headerHTML(activeNav);
  if (footerRoot) footerRoot.outerHTML = footerHTML();

  // theme
  document.documentElement.setAttribute('data-theme', localStorage.getItem('syra_theme') || 'light');

  // header state (cart badge + account link)
  if (typeof Cart !== 'undefined') Cart.refreshBadge();
  const accountLink = document.getElementById('account-link');
  if (accountLink && typeof Auth !== 'undefined' && Auth.isLoggedIn()) {
    accountLink.href = '/pages/profile.html';
  }

  // search form
  const form = document.getElementById('search-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const q = form.querySelector('input').value.trim();
      if (q) window.location.href = `/pages/search.html?q=${encodeURIComponent(q)}`;
    });
  }

  const mobileToggle = document.getElementById('mobile-nav-toggle');
  if (mobileToggle) {
    mobileToggle.addEventListener('click', () => document.querySelector('.main-nav').classList.toggle('open'));
  }
}

function toggleTheme() {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('syra_theme', next);
}
