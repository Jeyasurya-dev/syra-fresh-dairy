/**
 * SYRA Fresh — Main Frontend Logic
 * Handles: dark/light theme, header state, homepage sections (categories,
 * featured, bestsellers, offers, testimonials), and shared product-card rendering.
 * If the API is unreachable, DEMO_* fallback data keeps the page looking alive
 * so the storefront never renders empty during setup/preview.
 */

// ---------- Theme ----------
(function initTheme() {
  const saved = localStorage.getItem('syra_theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
})();

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('syra_theme', next);
}

// ---------- Demo fallback data (used only if the API can't be reached) ----------
const DEMO_CATEGORIES = [
  { id: 'dairy-products', name: 'Dairy Products', icon: '🥛', slug: 'dairy-products' },
  { id: 'ice-cream', name: 'Ice Cream', icon: '🍦', slug: 'ice-cream' },
  { id: 'healthy-snacks', name: 'Healthy Snacks', icon: '🥜', slug: 'healthy-snacks' },
  { id: 'fresh-fruits', name: 'Fresh Fruits', icon: '🍎', slug: 'fresh-fruits' },
];

const DEMO_IMAGES = {
  'dairy-products': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=500&q=80',
  'ice-cream': 'https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?w=500&q=80',
  'healthy-snacks': 'https://images.unsplash.com/photo-1599599810769-bcde5a160d32?w=500&q=80',
  'fresh-fruits': 'https://images.unsplash.com/photo-1610832958506-aa56368176cf?w=500&q=80',
};

const DEMO_PRODUCTS = [
  { id: 'd1', name: 'Full Cream Milk', category: 'dairy-products', price: 32, mrp: 35, unit: '500 ml', discount_percent: 9, rating_avg: 4.5, rating_count: 128, is_bestseller: true, images: [] },
  { id: 'd2', name: 'Farm Fresh Paneer', category: 'dairy-products', price: 90, mrp: 100, unit: '200 g', discount_percent: 10, rating_avg: 4.7, rating_count: 84, is_featured: true, images: [] },
  { id: 'i1', name: 'Belgian Chocolate Tub', category: 'ice-cream', price: 250, mrp: 299, unit: '700 ml', discount_percent: 16, rating_avg: 4.8, rating_count: 210, is_featured: true, images: [] },
  { id: 'i2', name: 'Mango Kulfi Sticks', category: 'ice-cream', price: 120, mrp: 140, unit: 'Pack of 4', discount_percent: 14, rating_avg: 4.6, rating_count: 95, is_bestseller: true, images: [] },
  { id: 's1', name: 'Premium California Almonds', category: 'healthy-snacks', price: 210, mrp: 240, unit: '250 g', discount_percent: 12, rating_avg: 4.4, rating_count: 66, is_bestseller: true, images: [] },
  { id: 's2', name: 'Crunchy Granola', category: 'healthy-snacks', price: 180, mrp: 210, unit: '400 g', discount_percent: 14, rating_avg: 4.3, rating_count: 41, images: [] },
  { id: 'f1', name: 'Alphonso Mangoes', category: 'fresh-fruits', price: 350, mrp: 400, unit: '1 kg', discount_percent: 12, rating_avg: 4.9, rating_count: 302, is_featured: true, is_bestseller: true, images: [] },
  { id: 'f2', name: 'Seedless Grapes', category: 'fresh-fruits', price: 90, mrp: 110, unit: '500 g', discount_percent: 18, rating_avg: 4.5, rating_count: 58, is_bestseller: true, images: [] },
];

const TESTIMONIALS = [
  { name: 'Priya R.', role: 'Chennai', text: 'The paneer and curd taste genuinely home-made fresh — delivery is always before 8am like promised.', rating: 5 },
  { name: 'Arvind K.', role: 'Bengaluru', text: 'Ordered the Belgian chocolate tub for a birthday — arrived rock solid and perfectly packed. Kids loved it.', rating: 5 },
  { name: 'Meera S.', role: 'Coimbatore', text: 'Love that I can track every order stage. The almonds and granola have become a weekly staple.', rating: 4 },
];

// ---------- Rendering helpers ----------
function starString(rating) {
  const full = Math.round(rating);
  return '★'.repeat(full) + '☆'.repeat(5 - full);
}

function productCardHTML(p) {
  const image = (p.images && p.images[0]) ? resolveImage(p.images[0]) : (DEMO_IMAGES[p.category] || DEMO_IMAGES['fresh-fruits']);
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
          <button class="add-btn" aria-label="Add to cart" onclick="Cart.add('${p.id}')">
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

function testimonialHTML(t) {
  return `
    <div class="testimonial-card">
      <div class="stars">${starString(t.rating)}</div>
      <p>"${t.text}"</p>
      <div class="testimonial-person">
        <div class="testimonial-avatar">${t.name.charAt(0)}</div>
        <div><strong>${t.name}</strong><span>${t.role}</span></div>
      </div>
    </div>`;
}

// ---------- Section loaders ----------
async function loadCategories() {
  const el = document.getElementById('category-grid');
  if (!el) return;
  try {
    const data = await Api.get('/categories');
    el.innerHTML = data.categories.map(categoryCardHTML).join('');
  } catch (e) {
    el.innerHTML = DEMO_CATEGORIES.map(categoryCardHTML).join('');
  }
}

async function loadProductSection(endpoint, elId, fallbackFilter) {
  const el = document.getElementById(elId);
  if (!el) return;
  try {
    const data = await Api.get(endpoint);
    el.innerHTML = data.products.map(productCardHTML).join('') || `<p class="empty-state">No products yet — add some from the admin panel.</p>`;
  } catch (e) {
    const fallback = DEMO_PRODUCTS.filter(fallbackFilter);
    el.innerHTML = fallback.map(productCardHTML).join('');
  }
}

function loadTestimonials() {
  const el = document.getElementById('testimonial-grid');
  if (!el) return;
  el.innerHTML = TESTIMONIALS.map(testimonialHTML).join('');
}

function initHeaderState() {
  Cart.refreshBadge();
  const accountLink = document.getElementById('account-link');
  if (accountLink && Auth.isLoggedIn()) {
    accountLink.href = '/pages/profile.html';
  }
}

function initSearch() {
  const form = document.getElementById('search-form');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const q = form.querySelector('input').value.trim();
    if (q) window.location.href = `/pages/shop.html?q=${encodeURIComponent(q)}`;
  });
}

document.addEventListener('DOMContentLoaded', () => {
  loadCategories();
  loadProductSection('/products/featured', 'featured-grid', (p) => p.is_featured);
  loadProductSection('/products/bestsellers', 'bestseller-grid', (p) => p.is_bestseller);
  loadProductSection('/products/offers', 'offers-grid', (p) => p.discount_percent >= 12);
  loadTestimonials();
  initHeaderState();
  initSearch();

  const mobileToggle = document.getElementById('mobile-nav-toggle');
  if (mobileToggle) {
    mobileToggle.addEventListener('click', () => {
      document.querySelector('.main-nav').classList.toggle('open');
    });
  }
});
