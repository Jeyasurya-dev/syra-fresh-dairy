/**
 * SYRA Fresh — Cart & Wishlist Helpers
 * Server-backed cart for logged-in users (each call hits the API so cart
 * state is consistent across devices). Falls back to a friendly prompt
 * to log in when a guest tries to add an item.
 */
const Cart = {
  async get() {
    if (!Auth.isLoggedIn()) return { items: [], subtotal: 0, item_count: 0 };
    const data = await Api.get('/cart', true);
    return data.cart;
  },

  async add(productId, quantity = 1) {
    if (!Auth.isLoggedIn()) {
      showToast('Please log in to add items to your cart');
      setTimeout(() => (window.location.href = '/pages/login.html'), 900);
      return null;
    }
    const data = await Api.post('/cart/items', { product_id: productId, quantity }, true);
    this.syncBadge(data.cart.item_count);
    showToast('Added to cart');
    return data.cart;
  },

  async updateQuantity(productId, quantity) {
    const data = await Api.put(`/cart/items/${productId}`, { quantity }, true);
    this.syncBadge(data.cart.item_count);
    return data.cart;
  },

  async remove(productId) {
    const data = await Api.del(`/cart/items/${productId}`, true);
    this.syncBadge(data.cart.item_count);
    return data.cart;
  },

  async refreshBadge() {
    if (!Auth.isLoggedIn()) return this.syncBadge(0);
    try {
      const cart = await this.get();
      this.syncBadge(cart.item_count);
    } catch (e) { /* silent — badge just won't update */ }
  },

  syncBadge(count) {
    document.querySelectorAll('.cart-badge').forEach((el) => {
      el.textContent = count;
      el.style.display = count > 0 ? 'flex' : 'none';
    });
  },
};

const Wishlist = {
  async toggle(productId, btnEl) {
    if (!Auth.isLoggedIn()) {
      showToast('Please log in to save items to your wishlist');
      return;
    }
    const isActive = btnEl.classList.contains('active');
    try {
      if (isActive) {
        await Api.del(`/wishlist/${productId}`, true);
        btnEl.classList.remove('active');
      } else {
        await Api.post(`/wishlist/${productId}`, {}, true);
        btnEl.classList.add('active');
        showToast('Saved to wishlist');
      }
    } catch (e) {
      showToast(e.message);
    }
  },
};

function showToast(message) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('show'), 2400);
}
