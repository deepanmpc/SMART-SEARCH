/* ============================================================
   SMART SEARCH — Website Script
   Handles: navbar scroll, animations, typing effect, mobile menu
   ============================================================ */

// ─── Navbar scroll effect ───
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  if (window.scrollY > 20) {
    navbar.classList.add('scrolled');
  } else {
    navbar.classList.remove('scrolled');
  }
});

// ─── Mobile menu ───
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const mobileMenu = document.getElementById('mobileMenu');
mobileMenuBtn.addEventListener('click', () => {
  mobileMenu.classList.toggle('hidden');
  mobileMenuBtn.textContent = mobileMenu.classList.contains('hidden') ? '☰' : '✕';
});
mobileMenu.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => {
    mobileMenu.classList.add('hidden');
    mobileMenuBtn.textContent = '☰';
  });
});

// ─── Scroll reveal animation ───
const revealEls = document.querySelectorAll(
  '.feature-card, .pipeline-step, .download-card, .doc-card, .demo-step, .stat-item, .shortcut-item'
);
revealEls.forEach(el => el.classList.add('reveal'));

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => entry.target.classList.add('visible'), i * 60);
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -60px 0px' });

revealEls.forEach(el => revealObserver.observe(el));

// ─── Hero typing effect ───
const phrases = [
  'photo of sunset at beach',
  'Q4 revenue chart screenshot',
  'machine learning notes',
  'video of birthday party 2024',
  'PDF about neural networks',
  'code review comments',
  'audio recording from meeting',
];
let phraseIndex = 0;
let charIndex = 0;
let isDeleting = false;
const typingEl = document.getElementById('typingText');

function typeLoop() {
  if (!typingEl) return;
  const currentPhrase = phrases[phraseIndex];

  if (isDeleting) {
    typingEl.textContent = currentPhrase.substring(0, charIndex - 1);
    charIndex--;
  } else {
    typingEl.textContent = currentPhrase.substring(0, charIndex + 1);
    charIndex++;
  }

  let delay = isDeleting ? 40 : 80;

  if (!isDeleting && charIndex === currentPhrase.length) {
    delay = 2200;
    isDeleting = true;
  } else if (isDeleting && charIndex === 0) {
    isDeleting = false;
    phraseIndex = (phraseIndex + 1) % phrases.length;
    delay = 400;
  }

  setTimeout(typeLoop, delay);
}
typeLoop();

// ─── Demo steps active state ───
const demoSteps = document.querySelectorAll('.demo-step');
let activeDemoStep = 0;
setInterval(() => {
  demoSteps.forEach((s, i) => {
    s.removeAttribute('data-active');
  });
  activeDemoStep = (activeDemoStep + 1) % demoSteps.length;
  demoSteps[activeDemoStep].setAttribute('data-active', 'true');
}, 2500);

// ─── Smooth scroll for anchor links ───
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', (e) => {
    const href = a.getAttribute('href');
    if (href === '#') return;
    const target = document.querySelector(href);
    if (target) {
      e.preventDefault();
      const offset = 80;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    }
  });
});

// ─── Download platform detection ───
function detectPlatform() {
  const ua = navigator.userAgent;
  let os = 'macOS';
  if (ua.includes('Windows')) os = 'Windows';
  else if (ua.includes('Linux')) os = 'Linux';

  const cards = document.querySelectorAll('.download-card');
  cards.forEach(card => card.classList.remove('featured'));
  cards.forEach(card => {
    const platform = card.querySelector('.download-platform');
    if (platform && platform.textContent.trim() === os) {
      card.classList.add('featured');
    }
  });
}
detectPlatform();

// ─── Orb parallax ───
document.addEventListener('mousemove', (e) => {
  const orbs = document.querySelectorAll('.orb');
  const { clientX, clientY } = e;
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight / 2;
  const dx = (clientX - cx) / cx;
  const dy = (clientY - cy) / cy;

  orbs.forEach((orb, i) => {
    const factor = (i + 1) * 15;
    orb.style.transform = `translate(${dx * factor}px, ${dy * factor}px)`;
  });
});

// ─── Stats counter animation ───
const statNumbers = document.querySelectorAll('.stat-number');
const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      statsObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.5 });
statNumbers.forEach(el => {
  el.style.transition = 'opacity 0.5s ease';
  statsObserver.observe(el);
});
