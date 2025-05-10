// Mobile Menu Toggle
const menuToggle = document.getElementById('menu-toggle');
const navLinks = document.querySelector('.nav-links');

menuToggle.addEventListener('click', () => {
  navLinks.classList.toggle('active');
});

// Scroll reveal effect
const revealElements = document.querySelectorAll('.reveal');

function reveal() {
  revealElements.forEach(el => {
    const windowHeight = window.innerHeight;
    const elementTop = el.getBoundingClientRect().top;
    const revealPoint = 150;

    if (elementTop < windowHeight - revealPoint) {
      el.classList.add('active');
    }
  });
}

window.addEventListener('scroll', reveal);
window.addEventListener('load', reveal);


const qrContainer = document.getElementById('qr-particles');

// How many QR particles
const particleCount = 150;

for (let i = 0; i < particleCount; i++) {
  const qr = document.createElement('div');
  qr.classList.add('qr-particle');
  
  qr.style.top = Math.random() * window.innerHeight + 'px';
  qr.style.left = Math.random() * window.innerWidth + 'px';

  // Each particle will have a slightly different speed
  const duration = 20 + Math.random() * 30; // between 20s - 50s
  qr.style.animationDuration = `${duration}s`;

  // Slightly different animation delays
  qr.style.animationDelay = `${Math.random() * 20}s`;

  // Vary the opacity a bit
  qr.style.opacity = 0.02 + Math.random() * 0.08;
  
  qrContainer.appendChild(qr);
}
