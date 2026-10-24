/* ============================================
   CAR-T Therapy China — MedTourChina
   Core JavaScript — Chatwoot live-chat contact channel

   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initFAQ();
  initChatwootTrigger();
  initScrollAnimations();
});

/* --- Mobile Navigation --- */
function initNavigation() {
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');
  if (!toggle || !links) return;

  toggle.addEventListener('click', () => {
    links.classList.toggle('open');
    const isOpen = links.classList.contains('open');
    toggle.setAttribute('aria-expanded', isOpen);
  });

  document.addEventListener('click', (e) => {
    if (!toggle.contains(e.target) && !links.contains(e.target)) {
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });
}

/* --- FAQ Accordion --- */
function initFAQ() {
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.parentElement;
      const isOpen = item.classList.contains('open');

      // Close all others
      document.querySelectorAll('.faq-item.open').forEach(open => {
        if (open !== item) open.classList.remove('open');
      });

      item.classList.toggle('open', !isOpen);
    });
  });
}

/* --- Chatwoot live-chat trigger ---
   [data-chatwoot-open] elements open the Chatwoot website widget.
   window.$chatwoot is provided by the per-page SDK snippet. */
function initChatwootTrigger() {
  const triggers = document.querySelectorAll('[data-chatwoot-open]');
  if (!triggers.length) return;

  triggers.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      if (window.$chatwoot && typeof window.$chatwoot.toggle === 'function') {
        window.$chatwoot.toggle('open');
      } else {
        showToast('Chat is loading… if it does not open, please email info@healthtourchina.net or use WhatsApp.', true);
      }
    });
  });
}

function showToast(message, isError = false) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.background = isError ? 'var(--danger)' : 'var(--success)';
  toast.textContent = message;
  document.body.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/* --- Scroll Animations --- */
function initScrollAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

  document.querySelectorAll('.animate-on-scroll').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
  });
}
