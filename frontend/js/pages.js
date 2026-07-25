/**
 * SYRA Fresh — Shared helpers for inner pages
 * (search, wishlist, categories, profile, orders, order-tracking, faq...)
 * Loaded after api.js / auth.js / cart.js on any page that needs them.
 */

// ---------- Formatting ----------
function formatDate(iso, opts) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', opts || { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function slugifyStatus(status) {
  return (status || '').toLowerCase().replace(/\s+/g, '-');
}

function statusBadgeHTML(status) {
  return `<span class="badge-status st-${slugifyStatus(status)}">${status}</span>`;
}

function debounce(fn, wait = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
}

// ---------- Accordion (FAQ etc.) ----------
function toggleAccordion(headerEl) {
  const item = headerEl.closest('.accordion-item');
  const wasOpen = item.classList.contains('open');
  item.parentElement.querySelectorAll('.accordion-item.open').forEach((el) => {
    if (el !== item) el.classList.remove('open');
  });
  item.classList.toggle('open', !wasOpen);
}

// ---------- Generic vertical/horizontal tab switch ----------
function switchTabGroup(navSelector, panelSelector, key) {
  document.querySelectorAll(navSelector).forEach((btn) => btn.classList.toggle('active', btn.dataset.tab === key));
  document.querySelectorAll(panelSelector).forEach((panel) => panel.classList.toggle('active', panel.dataset.panel === key));
}

// ---------- Wishlist state sync on product grids ----------
// Fetches the logged-in user's wishlist once and marks matching product
// cards (elements with [data-id]) with the .active wishlist-btn state.
async function syncWishlistState(root = document) {
  if (!Auth.isLoggedIn()) return;
  try {
    const data = await Api.get('/wishlist', true);
    const ids = new Set((data.products || []).map((p) => p.id));
    root.querySelectorAll('[data-id]').forEach((card) => {
      if (ids.has(card.dataset.id)) {
        const btn = card.querySelector('.wishlist-btn');
        if (btn) btn.classList.add('active');
      }
    });
  } catch (e) { /* silent */ }
}

// ---------- Recent searches (localStorage) ----------
const RecentSearches = {
  key: 'syra_recent_searches',
  get() {
    try { return JSON.parse(localStorage.getItem(this.key)) || []; } catch (e) { return []; }
  },
  add(term) {
    if (!term) return;
    let list = this.get().filter((t) => t.toLowerCase() !== term.toLowerCase());
    list.unshift(term);
    list = list.slice(0, 8);
    localStorage.setItem(this.key, JSON.stringify(list));
  },
  clear() { localStorage.removeItem(this.key); },
};

// ---------- Star rating (read-only render used across pages) ----------
function starString(rating) {
  const full = Math.round(rating || 0);
  return '★'.repeat(Math.max(0, full)) + '☆'.repeat(Math.max(0, 5 - full));
}

// ---------- Shared card renderers (mirrors main.js, used on non-home pages) ----------
const PAGES_DEMO_IMAGES = {
  'dairy-products': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=500&q=80',
  'ice-cream': 'https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?w=500&q=80',
  'healthy-snacks': 'https://images.unsplash.com/photo-1599599810769-bcde5a160d32?w=500&q=80',
  'fresh-fruits': 'https://images.unsplash.com/photo-1610832958506-aa56368176cf?w=500&q=80',
};

function productCardHTML(p) {
  const image = (p.images && p.images[0]) ? resolveImage(p.images[0]) : (PAGES_DEMO_IMAGES[p.category] || PAGES_DEMO_IMAGES['fresh-fruits']);
  const tag = p.discount_percent >= 15 ? `<span class="product-tag tag-berry">${p.discount_percent}% OFF</span>`
    : p.is_bestseller ? `<span class="product-tag">Bestseller</span>` : '';
  return `
    <article class="product-card" data-id="${p.id}">
      <div class="product-media">
        <a href="/pages/product-details.html?slug=${p.slug || p.id}">
          <img src="${image}" alt="${p.name}" loading="lazy">
        </a>
        ${tag}
        <button class="wishlist-btn" onclick="Wishlist.toggle('${p.id}', this)" aria-label="Save to wishlist">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>
        </button>
      </div>
      <div class="product-info">
        <span class="product-cat">${(p.category || '').replace('-', ' ')}</span>
        <h3 class="product-name">${p.name}</h3>
        <span class="product-unit">${p.unit || ''}</span>
        <div class="product-rating"><span class="stars">${starString(p.rating_avg || 4.5)}</span><span>(${p.rating_count || 0})</span></div>
        <div class="product-footer">
          <div class="price-row">
            <span class="price-current">₹${p.price}</span>
            ${p.mrp && p.mrp > p.price ? `<span class="price-mrp">₹${p.mrp}</span>` : ''}
          </div>
          <button class="add-btn" aria-label="Add to cart" onclick="Cart.add('${p.id}')" ${p.in_stock === false ? 'disabled' : ''}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
          </button>
        </div>
      </div>
    </article>`;
}

function categoryCardHTML(c) {
  return `
    <a class="category-card" href="/pages/shop.html?category=${c.slug}">
      <div class="category-icon-wrap">${c.icon || '🛒'}</div>
      <h3>${c.name}</h3>
      <p>Shop now</p>
    </a>`;
}

// ---------- Image resolver (mirrors api.js resolveImage; safe if api.js absent) ----------
if (typeof resolveImage === 'undefined') {
  window.resolveImage = function (path) {
    if (!path) return 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&q=80';
    if (path.startsWith('http')) return path;
    const base = window.SYRA_API_BASE || 'https://syra-fresh-backend.onrender.com/api';
    return `${base.replace('/api', '')}${path}`;
  };
}

// ---------- Mobile nav toggle (shared across pages with .main-nav) ----------
document.addEventListener('DOMContentLoaded', () => {
  const mobileToggle = document.getElementById('mobile-nav-toggle');
  const nav = document.querySelector('.main-nav');
  if (mobileToggle && nav) {
    mobileToggle.addEventListener('click', () => nav.classList.toggle('open'));
  }
});
