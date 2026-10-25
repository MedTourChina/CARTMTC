/* ============================================
   CAR-T Therapy China — MedTourChina
   Core JavaScript — Chatwoot live-chat contact channel

   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initFAQ();
  initChatwootTrigger();
  initContactFormChatwoot();
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

/* --- Contact form -> Chatwoot ---
   The inquiry form has no backend. On submit we attach the visitor's details to
   the Chatwoot contact (setUser + setCustomAttributes) AND send the full case
   summary as a real widget message, so a conversation is created and the agent
   gets notified. Success UI is shown only after delivery is attempted; if the
   widget can't load we fall back to email/WhatsApp instead of a false success. */
function initContactFormChatwoot() {
  const form = document.getElementById('inquiry-form');
  if (!form) return;
  const status = document.getElementById('form-status');
  const statusName = document.getElementById('form-status-name');

  // Run `cb` once the Chatwoot widget SDK is ready (or best-effort after a short wait).
  function whenChatwootReady(cb) {
    if (window.$chatwoot && typeof window.$chatwoot.setUser === 'function') {
      cb();
      return;
    }
    window.addEventListener('chatwoot:ready', cb, { once: true });
    const t = setInterval(() => {
      if (window.$chatwoot && typeof window.$chatwoot.setUser === 'function') {
        clearInterval(t);
        cb();
      }
    }, 300);
    setTimeout(() => clearInterval(t), 8000); // stop polling; watchdog decides fallback
  }

  function buildSummary(d) {
    return [
      'New CAR-T case-review request',
      d.name ? 'Name: ' + d.name : '',
      d.email ? 'Email: ' + d.email : '',
      d.phone ? 'WhatsApp/Phone: ' + d.phone : '',
      d.country ? 'Country: ' + d.country : '',
      d.interest ? 'Interest: ' + d.interest : '',
      d.message ? 'Diagnosis & history: ' + d.message : ''
    ].filter(Boolean).join('\n');
  }

  // Attach contact attributes, open the widget, then send the inquiry as a message
  // (retried briefly because the conversation may not exist yet on first open).
  function sendToChatwoot(d) {
    if (d.email) window.$chatwoot.setUser(d.email, { name: d.name, email: d.email });
    const attrs = { phone: d.phone, country: d.country, interest: d.interest };
    if (d.message) attrs.inquiry = d.message.slice(0, 900);
    if (window.$chatwoot.setCustomAttributes) window.$chatwoot.setCustomAttributes(attrs);
    if (typeof window.$chatwoot.toggle === 'function') window.$chatwoot.toggle('open');

    const msg = buildSummary(d);
    let tries = 0;
    const attempt = () => {
      try {
        if (typeof window.$chatwoot.sendMessage === 'function') {
          window.$chatwoot.sendMessage(msg);
          return;
        }
      } catch (err) { /* retry below */ }
      if (tries++ < 15) setTimeout(attempt, 400);
    };
    setTimeout(attempt, 400);
  }

  function showSuccess(name) {
    if (!status) return;
    if (statusName && name) statusName.textContent = 'Thank you, ' + name + '.';
    form.style.display = 'none';
    status.style.display = 'block';
    status.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  // Real fallback: keep the form visible and point the visitor to email/WhatsApp.
  function showFallback() {
    showToast('Live chat is unavailable right now — please email info@healthtourchina.net or use WhatsApp. Your details are safe; you can try submitting again shortly.', true);
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const el = form.elements;
    const data = {
      name: (el['name'].value || '').trim(),
      email: (el['email'].value || '').trim(),
      phone: (el['phone'].value || '').trim(),
      country: (el['country'].value || '').trim(),
      interest: el['interest'].value || '',
      message: (el['message'].value || '').trim()
    };

    let done = false;
    const watchdog = setTimeout(() => {
      if (!done) { done = true; showFallback(); }
    }, 8500);

    whenChatwootReady(() => {
      if (done) return;
      try {
        sendToChatwoot(data);
        done = true;
        clearTimeout(watchdog);
        showSuccess(data.name);
      } catch (err) {
        done = true;
        clearTimeout(watchdog);
        showFallback();
      }
    });
  });
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
