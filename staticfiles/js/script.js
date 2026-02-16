// ========================================
// Initialize Lucide Icons
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
        lucide.createIcons();
    }
});

// ========================================
// Mobile Menu Toggle
// ========================================
document.addEventListener('DOMContentLoaded', function() {
  const mobileMenuToggle = document.getElementById('mobileMenuToggle');
  const mobileNav = document.getElementById('mobileNav');
  const menuIcon = document.getElementById('menuIcon');
  const closeIcon = document.getElementById('closeIcon');

  if (mobileMenuToggle && mobileNav) {
    mobileMenuToggle.addEventListener('click', function() {
      mobileNav.classList.toggle('active');
      if (mobileNav.classList.contains('active')) {
        menuIcon.style.display = 'none';
        closeIcon.style.display = 'block';
        document.body.style.overflow = 'hidden';
      } else {
        menuIcon.style.display = 'block';
        closeIcon.style.display = 'none';
        document.body.style.overflow = '';
      }
    });

    const mobileNavLinks = document.querySelectorAll('.nav-mobile .nav-link, .mobile-actions a');
    mobileNavLinks.forEach(link => {
      link.addEventListener('click', function() {
        mobileNav.classList.remove('active');
        menuIcon.style.display = 'block';
        closeIcon.style.display = 'none';
        document.body.style.overflow = '';
      });
    });

    document.addEventListener('click', function(event) {
      if (!event.target.closest('.header-content') && 
          !event.target.closest('.nav-mobile') && 
          mobileNav.classList.contains('active')) {
        mobileNav.classList.remove('active');
        menuIcon.style.display = 'block';
        closeIcon.style.display = 'none';
        document.body.style.overflow = '';
      }
    });
  }
  
  // Auto-dismiss alerts after 5 seconds
  setTimeout(function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 5000);
});

// ========================================
// Header Scroll Effect
// ========================================
const header = document.getElementById('header');
if (header) {
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        header.style.boxShadow = scrollTop > 100 
            ? '0 4px 20px -4px rgba(0, 0, 0, 0.1)' 
            : 'none';
    });
}

// ========================================
// Animation on Scroll (Intersection Observer)
// ========================================
const animatedElements = document.querySelectorAll('.step-card, .prize-card, .rules-card, .competition-card, .feature-card');
if (animatedElements.length > 0) {
    const observerOptions = { root: null, rootMargin: '0px', threshold: 0.1 };
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

// ========================================
// Competition Card Hover Effects
// ========================================
const competitionCards = document.querySelectorAll('.competition-card');
competitionCards.forEach(card => {
    card.addEventListener('mouseenter', function() {
        const badge = this.querySelector('.competition-badge');
        if (badge) badge.style.transform = 'scale(1.1)';
    });
    card.addEventListener('mouseleave', function() {
        const badge = this.querySelector('.competition-badge');
        if (badge) badge.style.transform = 'scale(1)';
    });
});

// ========================================
// Add CSS for spinner
// ========================================
const style = document.createElement('style');
style.textContent = `
    .spinner {
        display: inline-block;
        width: 1em;
        height: 1em;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: white;
        animation: spin 1s ease-in-out infinite;
        margin-right: 0.5rem;
    }
    
    @keyframes spin { to { transform: rotate(360deg); } }
`;
document.head.appendChild(style);
