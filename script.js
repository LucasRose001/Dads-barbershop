const toggle = document.querySelector('.nav-toggle');
const nav = document.getElementById('primary-nav');

toggle.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
});

nav.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => {
    nav.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  });
});

document.querySelectorAll('a[href="#top"]').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    history.replaceState(null, '', location.pathname);
  });
});

const fab = document.querySelector('.mobile-book-fab');
const bookSection = document.getElementById('book');
if (fab && bookSection && 'IntersectionObserver' in window) {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => fab.classList.toggle('hidden', entry.isIntersecting));
  }, { threshold: 0.2 });
  obs.observe(bookSection);
}

document.getElementById('year').textContent = new Date().getFullYear();

// ===== Scroll reveal animations =====
(function () {
  if (!('IntersectionObserver' in window)) return;

  const revealSelectors = [
    '.section-head',
    '.meet-quote',
    '.book-card',
    '.hours-table',
    '.visit-grid',
    '.map-wrap',
    '.products-brands',
    '.meet-grid'
  ];
  document.querySelectorAll(revealSelectors.join(',')).forEach(el => {
    el.classList.add('reveal');
  });
  document.querySelectorAll('.services-grid, .reviews-grid').forEach(el => {
    el.classList.add('reveal-stagger');
  });

  document.querySelectorAll('.review .stars').forEach(el => {
    const text = el.textContent.trim();
    el.innerHTML = [...text]
      .map(ch => `<span class="star" aria-hidden="true">${ch}</span>`)
      .join('');
  });

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -60px 0px' });

  document.querySelectorAll('.reveal, .reveal-stagger, .review').forEach(el => {
    observer.observe(el);
  });
})();

// ===== Today's day highlights in the hours table =====
(function () {
  const days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  const today = days[new Date().getDay()];
  document.querySelectorAll('.hours-row').forEach(row => {
    const dayCell = row.querySelector('span:first-child');
    if (dayCell && dayCell.textContent.trim() === today) {
      row.classList.add('today');
    }
  });
})();

// ===== Back-to-top floating button (desktop only) =====
(function () {
  if (window.matchMedia('(max-width: 860px)').matches) return;
  const btn = document.createElement('button');
  btn.className = 'back-to-top';
  btn.type = 'button';
  btn.setAttribute('aria-label', 'Back to top');
  btn.innerHTML = '↑';
  document.body.appendChild(btn);
  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      btn.classList.toggle('visible', window.scrollY > 600);
      ticking = false;
    });
  }, { passive: true });
})();
