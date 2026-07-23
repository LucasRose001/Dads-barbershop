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
