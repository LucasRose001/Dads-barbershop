// Mobile nav toggle
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

// Footer year
document.getElementById('year').textContent = new Date().getFullYear();

// Booking form — mailto handoff so it works without a backend
function handleBooking(e) {
  e.preventDefault();
  const form = e.target;
  const data = new FormData(form);
  const name = data.get('name');
  const phone = data.get('phone');
  const service = data.get('service');
  const when = data.get('when') || 'no preference given';
  const notes = data.get('notes') || '—';

  const subject = encodeURIComponent(`Booking request — ${name}`);
  const body = encodeURIComponent(
    `Name: ${name}\nPhone: ${phone}\nService: ${service}\nPreferred time: ${when}\n\nNotes:\n${notes}`
  );
  window.location.href = `mailto:hello@dadsbarbershop.ca?subject=${subject}&body=${body}`;

  form.hidden = true;
  form.parentElement.querySelector('.book-success').hidden = false;
  return false;
}
