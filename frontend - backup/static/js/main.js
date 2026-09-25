/**
 * SonicSentinel - Global UI, Theme Engine & Responsive Navigation
 */

document.addEventListener('DOMContentLoaded', () => {
  initThemeEngine();
  initNavDrawer();
  initVisualizerThemeChips();
  initAutoDismissAlerts();
});

// ==========================================
// Theme Engine (Day & Night Mode Switcher)
// ==========================================
function initThemeEngine() {
  const themeToggle = document.getElementById('themeToggleBtn');
  const dayOpt = document.querySelector('.switch-day');
  const nightOpt = document.querySelector('.switch-night');
  
  // Check localStorage or default to 'light' (Day mode)
  const savedTheme = localStorage.getItem('sonicsentinel_theme') || 'light';
  applyTheme(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', (e) => {
      // If clicked specifically on Day or Night, respect that
      if (dayOpt && dayOpt.contains(e.target)) {
        applyTheme('light');
        localStorage.setItem('sonicsentinel_theme', 'light');
        return;
      }
      if (nightOpt && nightOpt.contains(e.target)) {
        applyTheme('dark');
        localStorage.setItem('sonicsentinel_theme', 'dark');
        return;
      }

      // Otherwise toggle
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme);
      localStorage.setItem('sonicsentinel_theme', newTheme);
    });

    // Keyboard accessibility (Enter / Space)
    themeToggle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
        localStorage.setItem('sonicsentinel_theme', newTheme);
      }
    });
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  if (document.body) {
    document.body.setAttribute('data-theme', theme);
  }
  const themeToggle = document.getElementById('themeToggleBtn');
  
  if (themeToggle) {
    if (theme === 'light') {
      themeToggle.classList.remove('is-night');
      themeToggle.classList.add('is-day');
    } else {
      themeToggle.classList.remove('is-day');
      themeToggle.classList.add('is-night');
    }
  }

  // Update canvas theme default if not manually overridden
  const manualVisTheme = localStorage.getItem('sonicsentinel_vis_theme');
  if (!manualVisTheme) {
    applyVisualizerTheme(theme === 'light' ? 'lab' : 'sonar');
  }
}

// ==========================================
// Responsive Navigation Drawer (Mobile & Tablets)
// ==========================================
function initNavDrawer() {
  const toggleBtn = document.getElementById('navToggleBtn');
  const navMenu = document.getElementById('navMenu');

  if (!toggleBtn || !navMenu) return;

  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = navMenu.classList.toggle('open');
    toggleBtn.innerHTML = isOpen ? '<i class="fa-solid fa-xmark"></i>' : '<i class="fa-solid fa-bars"></i>';
    toggleBtn.setAttribute('aria-expanded', isOpen);
  });

  // Close when clicking any nav link
  navMenu.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', () => {
      navMenu.classList.remove('open');
      toggleBtn.innerHTML = '<i class="fa-solid fa-bars"></i>';
    });
  });

  // Close when clicking outside
  document.addEventListener('click', (e) => {
    if (navMenu.classList.contains('open') && !navMenu.contains(e.target) && !toggleBtn.contains(e.target)) {
      navMenu.classList.remove('open');
      toggleBtn.innerHTML = '<i class="fa-solid fa-bars"></i>';
    }
  });

  // Auto close on window resize past tablet breakpoint
  window.addEventListener('resize', () => {
    if (window.innerWidth > 1080 && navMenu.classList.contains('open')) {
      navMenu.classList.remove('open');
      toggleBtn.innerHTML = '<i class="fa-solid fa-bars"></i>';
    }
  });
}

// ==========================================
// Spectrogram & Visualizer Theme Switcher
// ==========================================
function initVisualizerThemeChips() {
  const savedVisTheme = localStorage.getItem('sonicsentinel_vis_theme') || (
    document.documentElement.getAttribute('data-theme') === 'dark' ? 'sonar' : 'lab'
  );
  
  applyVisualizerTheme(savedVisTheme);

  document.querySelectorAll('.vis-theme-chip').forEach(chip => {
    chip.addEventListener('click', (e) => {
      const vtheme = chip.getAttribute('data-vtheme');
      if (!vtheme) return;

      localStorage.setItem('sonicsentinel_vis_theme', vtheme);
      applyVisualizerTheme(vtheme);
    });
  });
}

function applyVisualizerTheme(themeKey) {
  const validThemes = ['lab', 'sonar', 'emerald', 'cyber'];
  if (!validThemes.includes(themeKey)) themeKey = 'lab';

  // Update all canvas wrappers
  document.querySelectorAll('.canvas-wrapper').forEach(wrapper => {
    validThemes.forEach(t => wrapper.classList.remove(`canvas-theme-${t}`));
    wrapper.classList.add(`canvas-theme-${themeKey}`);
  });

  // Update chip active states
  document.querySelectorAll('.vis-theme-chip').forEach(chip => {
    if (chip.getAttribute('data-vtheme') === themeKey) {
      chip.classList.add('active');
    } else {
      chip.classList.remove('active');
    }
  });

  // Dispatch custom event for visualizer redraws
  window.dispatchEvent(new CustomEvent('visThemeChanged', { detail: { theme: themeKey } }));
}

// Auto dismiss flash alerts after 5 seconds
function initAutoDismissAlerts() {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-10px)';
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });
}
