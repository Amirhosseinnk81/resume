document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const toggleBtn = document.getElementById('themeToggle');
  const scrollBtn = document.getElementById('scrollTopBtn');

  // === تم روشن/تاریک ===
  const savedTheme = localStorage.getItem('theme') || 'light';
  body.setAttribute('data-theme', savedTheme);
  updateIcon(savedTheme);

  function updateIcon(theme) {
    if (toggleBtn) toggleBtn.textContent = theme === 'dark' ? '🌙' : '🌞';
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = body.getAttribute('data-theme');
      const next = current === 'light' ? 'dark' : 'light';
      body.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      updateIcon(next);
    });
  }

  // === Navbar animation ===
  const navbar = document.querySelector('.navbar');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.classList.add('shrink', 'scrolled');
    } else {
      navbar.classList.remove('shrink', 'scrolled');
    }
    // دکمه برگشت به بالا
    if (scrollBtn)
      scrollBtn.style.display = window.scrollY > 300 ? 'flex' : 'none';
  });

  // === Scroll to top ===
  if (scrollBtn) {
    scrollBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // === Fade animation ===
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
