/**
 * NANO Tech Store — Brutalista Theme JS v3.0
 * Cart Slide-over | Notifications | Mobile Menu | Quantity
 */

'use strict';

/* ── CART MANAGER (Slide-over "Terminal de Compra") ─────── */
const CartManager = {
  overlay: null,
  panel: null,
  countEls: [],

  init() {
    this.createPanel();
    this.bindToggleBtns();
    this.refresh();
  },

  createPanel() {
    // Overlay wrapper
    const overlay = document.createElement('div');
    overlay.className = 'cart-overlay';
    overlay.setAttribute('aria-hidden', 'true');
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', 'Tu carrito');
    overlay.innerHTML = `
      <div class="cart-overlay__backdrop"></div>
      <div class="cart-panel">
        <div class="cart-panel__header">
          <span class="cart-panel__title">Tu carrito</span>
          <button class="cart-panel__close" aria-label="Cerrar carrito">&times;</button>
        </div>
        <div class="cart-panel__body" id="cart-panel-body">
          <div class="cart-panel__empty">
            <div class="cart-panel__empty-icon">🛒</div>
            <p class="cart-panel__empty-text">Tu carrito está vacío</p>
            <p class="cart-panel__empty-hint">Añade productos para continuar.</p>
          </div>
        </div>
        <div class="cart-panel__footer" id="cart-panel-footer" style="display:none">
          <div class="cart-panel__subtotal">
            <span class="cart-panel__subtotal-label">Subtotal</span>
            <span class="cart-panel__subtotal-value" id="cart-panel-total">$0</span>
          </div>
          <a href="/checkout" class="cart-panel__checkout" id="cart-panel-checkout">
            Ir al checkout
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </a>
          <p class="cart-panel__secure">🔒 Pago seguro cifrado por Shopify</p>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    this.overlay = overlay;
    this.panel = overlay.querySelector('.cart-panel');

    // Close on backdrop
    overlay.querySelector('.cart-overlay__backdrop').addEventListener('click', () => this.close());
    overlay.querySelector('.cart-panel__close').addEventListener('click', () => this.close());

    // ESC key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.overlay.classList.contains('is-open')) this.close();
    });
  },

  bindToggleBtns() {
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.cart-toggle-btn, [data-cart-toggle]');
      if (btn) { e.preventDefault(); this.open(); }
    });
  },

  open() {
    this.overlay.classList.add('is-open');
    this.overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    this.refresh();
  },

  close() {
    this.overlay.classList.remove('is-open');
    this.overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  },

  async refresh() {
    try {
      const res = await fetch('/cart.js');
      const cart = await res.json();
      this.renderItems(cart);
      this.updateCount(cart.item_count);
    } catch (e) {
      console.warn('Cart fetch error:', e);
    }
  },

  formatMoney(cents) {
    const currency = window.Shopify?.currency?.active || 'COP';
    const decimals = ['COP','CLP','JPY','KRW'].includes(currency) ? 0 : 2;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: decimals
    }).format(cents / 100);
  },

  renderItems(cart) {
    const body = document.getElementById('cart-panel-body');
    const footer = document.getElementById('cart-panel-footer');
    const totalEl = document.getElementById('cart-panel-total');

    if (!body) return;

    if (!cart.items || cart.items.length === 0) {
      body.innerHTML = `
        <div class="cart-panel__empty">
          <div class="cart-panel__empty-icon">🛒</div>
          <p class="cart-panel__empty-text">Tu carrito está vacío</p>
          <p class="cart-panel__empty-hint">Añade productos para continuar.</p>
        </div>`;
      if (footer) footer.style.display = 'none';
      return;
    }

    body.innerHTML = cart.items.map((item, index) => `
      <div class="cart-item" data-index="${item.key}">
        <img
          class="cart-item__image"
          src="${item.image ? item.image.replace('http:', 'https:') : ''}"
          alt="${item.title}"
          loading="lazy"
          onerror="this.style.display='none'"
        >
        <div class="cart-item__info">
          <p class="cart-item__title">${item.product_title}</p>
          ${item.variant_title ? `<p class="cart-item__variant">${item.variant_title}</p>` : ''}
          <p class="cart-item__price">${this.formatMoney(item.final_line_price)}</p>
          <div class="cart-item__qty">
            <button class="cart-item__qty-btn" data-qty-change="-1" data-key="${item.key}" aria-label="Reducir cantidad">&#8722;</button>
            <span class="cart-item__qty-val">${item.quantity}</span>
            <button class="cart-item__qty-btn" data-qty-change="1" data-key="${item.key}" aria-label="Aumentar cantidad">&#43;</button>
          </div>
        </div>
        <div class="cart-item__actions">
          <button class="cart-item__remove" data-key="${item.key}" aria-label="Eliminar ${item.title}">&times;</button>
        </div>
      </div>
    `).join('');

    if (footer) {
      footer.style.display = 'block';
      if (totalEl) totalEl.textContent = this.formatMoney(cart.total_price);
    }

    // Bind qty & remove buttons
    body.querySelectorAll('[data-qty-change]').forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.dataset.key;
        const change = parseInt(btn.dataset.qtyChange);
        const item = cart.items.find(i => i.key === key);
        if (item) this.updateQty(key, item.quantity + change);
      });
    });

    body.querySelectorAll('[data-key].cart-item__remove').forEach(btn => {
      btn.addEventListener('click', () => this.updateQty(btn.dataset.key, 0));
    });
  },

  async updateQty(key, qty) {
    try {
      const res = await fetch('/cart/change.js', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: key, quantity: Math.max(0, qty) })
      });
      await res.json();
      this.refresh();
    } catch (e) {
      console.warn('Cart update error:', e);
    }
  },

  updateCount(count) {
    document.querySelectorAll('[data-cart-count]').forEach(el => {
      el.textContent = count;
    });
  }
};

/* ── ADD TO CART ────────────────────────────────────────── */
const AddToCart = {
  init() {
    document.addEventListener('submit', async (e) => {
      const form = e.target.closest('form[action="/cart/add"]');
      if (!form) return;
      const submitter = e.submitter;
      if (submitter && submitter.name === 'checkout') return;
      e.preventDefault();

      const btn = form.querySelector('[type="submit"]');
      const originalText = btn ? btn.innerHTML : '';
      if (btn) { btn.disabled = true; btn.innerHTML = 'AGREGANDO...'; }

      try {
        const formData = new FormData(form);
        const res = await fetch('/cart/add.js', {
          method: 'POST',
          headers: { 'Accept': 'application/json' },
          body: formData
        });

        if (!res.ok) throw new Error('Error al agregar');
        const item = await res.json();

        NotificationManager.show(`✓ ${item.title} agregado al carrito`, 'success');
        CartManager.refresh();
        CartManager.open();
      } catch (err) {
        NotificationManager.show('Error al agregar el producto', 'error');
      } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
      }
    });
  }
};

/* ── NOTIFICATION MANAGER ─────────────────────────────── */
const NotificationManager = {
  container: null,

  init() {
    this.container = document.createElement('div');
    this.container.className = 'notification-container';
    document.body.appendChild(this.container);

    // Make globally accessible
    window.showNotification = (msg, type) => this.show(msg, type);
  },

  show(message, type = 'success') {
    const el = document.createElement('div');
    el.className = `notification notification--${type}`;
    el.textContent = message;
    this.container.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }
};

/* ── MOBILE MENU ──────────────────────────────────────── */
const MobileMenu = {
  init() {
    const openBtn = document.querySelector('.mobile-menu-btn');
    const closeBtn = document.querySelector('.mobile-menu__close');
    const menu = document.querySelector('.mobile-menu');
    const backdrop = document.getElementById('mobile-backdrop');

    if (!menu) return;

    const openMenu = () => {
      menu.classList.add('is-open');
      if (backdrop) backdrop.classList.add('is-open');
      menu.setAttribute('aria-hidden', 'false');
      if (openBtn) openBtn.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    };

    const closeMenu = () => {
      menu.classList.remove('is-open');
      if (backdrop) backdrop.classList.remove('is-open');
      menu.setAttribute('aria-hidden', 'true');
      if (openBtn) openBtn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    };

    if (openBtn) openBtn.addEventListener('click', openMenu);
    if (closeBtn) closeBtn.addEventListener('click', closeMenu);
    if (backdrop) backdrop.addEventListener('click', closeMenu);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && menu.classList.contains('is-open')) closeMenu();
    });

    const accordionBtn = menu.querySelector('.mobile-menu__accordion-btn');
    const accordionPanel = menu.querySelector('.mobile-menu__accordion-panel');
    if (accordionBtn && accordionPanel) {
      accordionBtn.addEventListener('click', () => {
        const expanded = accordionBtn.getAttribute('aria-expanded') === 'true';
        accordionBtn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
        accordionPanel.hidden = expanded;
        const sign = accordionBtn.querySelector('span');
        if (sign) sign.textContent = expanded ? '+' : '-';
      });
    }
  }
};

/* ── MEGA MENU ─────────────────────────────────────────── */
const MegaMenu = {
  init() {
    const trigger = document.querySelector('.site-nav__trigger');
    const item = document.querySelector('.site-nav__item--mega');
    if (!trigger || !item) return;

    const open = () => trigger.setAttribute('aria-expanded', 'true');
    const close = () => trigger.setAttribute('aria-expanded', 'false');
    item.addEventListener('mouseenter', open);
    item.addEventListener('mouseleave', close);
    trigger.addEventListener('focus', open);
    item.addEventListener('focusout', (e) => {
      if (!item.contains(e.relatedTarget)) close();
    });
  }
};

/* ── HERO SLIDER ───────────────────────────────────────── */
const HeroSlider = {
  init() {
    const root = document.querySelector('[data-hero-slider]');
    if (!root) return;
    const slides = [...root.querySelectorAll('[data-hero-slide]')];
    if (!slides.length) return;
    const dots = [...root.querySelectorAll('[data-hero-dot]')];
    const prev = root.querySelector('[data-hero-prev]');
    const next = root.querySelector('[data-hero-next]');
    let current = 0;
    let timer = null;

    const show = (index) => {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, i) => slide.classList.toggle('is-active', i === current));
      dots.forEach((dot, i) => dot.classList.toggle('is-active', i === current));
    };

    const play = () => {
      const autoplay = root.dataset.autoplay === 'true';
      const speed = (parseInt(root.dataset.speed || '5', 10) || 5) * 1000;
      if (!autoplay || slides.length < 2) return;
      clearInterval(timer);
      timer = setInterval(() => show(current + 1), speed);
    };

    prev?.addEventListener('click', () => { show(current - 1); play(); });
    next?.addEventListener('click', () => { show(current + 1); play(); });
    dots.forEach((dot) => {
      dot.addEventListener('click', () => {
        show(parseInt(dot.dataset.heroDot || '0', 10));
        play();
      });
    });

    show(0);
    play();
  }
};

/* ── TESTIMONIALS CAROUSEL ─────────────────────────────── */
const Testimonials = {
  init() {
    const root = document.querySelector('[data-testimonials]');
    if (!root) return;
    const cards = [...root.querySelectorAll('[data-testimonial]')];
    const dots = [...root.querySelectorAll('[data-testimonial-dot]')];
    if (cards.length < 2) return;
    let current = 0;

    const show = (index) => {
      current = (index + cards.length) % cards.length;
      cards.forEach((card, i) => card.classList.toggle('is-active', i === current));
      dots.forEach((dot, i) => dot.classList.toggle('is-active', i === current));
    };

    dots.forEach((dot) => {
      dot.addEventListener('click', () => show(parseInt(dot.dataset.testimonialDot || '0', 10)));
    });

    setInterval(() => show(current + 1), 6000);
  }
};

/* ── QUANTITY SELECTOR (product page) ─────────────────── */
const QuantityManager = {
  init() {
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.product-form__qty-btn');
      if (!btn) return;
      const input = btn.closest('.product-form__qty')?.querySelector('.product-form__qty-input');
      if (!input) return;
      const current = parseInt(input.value) || 1;
      const isIncrease = btn.textContent.trim() === '+';
      input.value = Math.max(1, current + (isIncrease ? 1 : -1));
    });
  }
};

/* ── GALLERY (product page) ────────────────────────────── */
const Gallery = {
  init() {
    document.addEventListener('click', (e) => {
      const thumb = e.target.closest('.product-gallery__thumb');
      if (!thumb) return;
      const src = thumb.dataset.src;
      const main = document.querySelector('.product-gallery__main img');
      if (main && src) main.src = src;
      document.querySelectorAll('.product-gallery__thumb').forEach(t => t.classList.remove('active'));
      thumb.classList.add('active');
    });
  }
};

/* ── FILTER TABS (collection/featured section) ─────────── */
const FilterTabs = {
  init() {
    document.addEventListener('click', (e) => {
      const tab = e.target.closest('.filter-tab');
      if (!tab) return;

      const container = tab.closest('[data-filter-container]');
      if (!container) return;

      container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const filter = tab.dataset.filter;
      container.querySelectorAll('[data-tags]').forEach(item => {
        const tags = item.dataset.tags || '';
        const match = filter === 'all' || tags.split(' ').includes(filter);

        if (match) {
          item.classList.remove('is-hidden');
          item.classList.add('is-visible');
        } else {
          item.classList.remove('is-visible');
          item.classList.add('is-hidden');
        }
      });
    });
  }
};

/* ── INIT ──────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  NotificationManager.init();
  CartManager.init();
  AddToCart.init();
  MobileMenu.init();
  QuantityManager.init();
  Gallery.init();
  FilterTabs.init();
  MegaMenu.init();
  HeroSlider.init();
  Testimonials.init();
});
