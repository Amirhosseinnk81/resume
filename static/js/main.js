document.addEventListener('DOMContentLoaded', () => {
const body = document.body;
const toggleBtn = document.getElementById('themeToggle');


// آیکون داینامیک تم
function updateIcon(theme) {
toggleBtn.textContent = theme === 'dark' ? '🌙' : '🌞';
}


const savedTheme = localStorage.getItem('theme') || 'light';
body.setAttribute('data-theme', savedTheme);
updateIcon(savedTheme);


if (toggleBtn) {
toggleBtn.addEventListener('click', () => {
const current = body.getAttribute('data-theme');
const next = current === 'light' ? 'dark' : 'light';
body.setAttribute('data-theme', next);
localStorage.setItem('theme', next);
updateIcon(next);
});
}


// انیمیشن fade-in برای timeline
const fadeItems = document.querySelectorAll('.fade-item');
const observer = new IntersectionObserver(entries => {
entries.forEach(entry => {
if (entry.isIntersecting) {
entry.target.classList.add('visible');
observer.unobserve(entry.target);
}
});
}, { threshold: 0.2 });


fadeItems.forEach(item => observer.observe(item));
});
window.addEventListener("scroll", function() {
  const navbar = document.querySelector(".navbar");
  if (window.scrollY > 50) {
    navbar.classList.add("shrink");
  } else {
    navbar.classList.remove("shrink");
  }
});
