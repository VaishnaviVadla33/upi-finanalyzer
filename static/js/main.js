// Main JavaScript for FinAnalyzer

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    // Enhanced navbar scroll effect
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', () => {
        const currentScrollY = window.scrollY;
        
        if (currentScrollY > 100) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Smooth scrolling with enhanced animation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Add bounce effect to target
                target.style.animation = 'targetBounce 0.6s ease-out';
                setTimeout(() => {
                    target.style.animation = '';
                }, 600);
            }
        });
    });

    // Enhanced scroll animations with Intersection Observer
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // Observe feature cards with staggered animation
    document.querySelectorAll('.feature-card').forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(50px)';
        card.style.transition = `opacity 0.8s ease ${index * 0.1}s, transform 0.8s ease ${index * 0.1}s`;
        observer.observe(card);
    });

    // Enhanced dashboard preview animation
    const dashboardPreview = document.querySelector('.dashboard-preview');
    if (dashboardPreview) {
        const previewObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Animate chart bars with staggered effect
                    const bars = entry.target.querySelectorAll('.bar');
                    bars.forEach((bar, index) => {
                        setTimeout(() => {
                            bar.style.animation = `growUp 1.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards`;
                        }, index * 150);
                    });
                    
                    // Animate stats
                    const stats = entry.target.querySelectorAll('.preview-stat');
                    stats.forEach((stat, index) => {
                        setTimeout(() => {
                            stat.style.animation = `slideInRight 0.8s ease forwards`;
                        }, index * 100);
                    });
                }
            });
        }, { threshold: 0.3 });
        
        previewObserver.observe(dashboardPreview);
    }

    // Enhanced button interactions
    document.querySelectorAll('.btn').forEach(btn => {
        // Ripple effect
        btn.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s ease-out;
                pointer-events: none;
            `;
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
            
            // Loading state for auth buttons
            if (this.href && this.href.includes('/auth')) {
                this.style.opacity = '0.8';
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            }
        });
        
        // Hover effects
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px) scale(1.02)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });

    // Parallax effect for hero section
    const hero = document.querySelector('.hero');
    if (hero) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const rate = scrolled * -0.5;
            hero.style.transform = `translateY(${rate}px)`;
        });
    }

    // Typing animation for hero title (disabled to prevent HTML showing)
    const heroTitle = document.querySelector('.hero-title');
    if (heroTitle) {
        // Just ensure the title is visible, no typing animation
        heroTitle.style.opacity = '1';
    }

    // Counter animation for stats
    const animateCounter = (element, target, duration = 2000) => {
        let start = 0;
        const increment = target / (duration / 16);
        
        const timer = setInterval(() => {
            start += increment;
            if (start >= target) {
                element.textContent = target.toLocaleString();
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(start).toLocaleString();
            }
        }, 16);
    };

    // Animate stats when they come into view
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const statNumber = entry.target.querySelector('.stat-number');
                if (statNumber && !statNumber.classList.contains('animated')) {
                    statNumber.classList.add('animated');
                    const text = statNumber.textContent;
                    const number = parseInt(text.replace(/[^\d]/g, ''));
                    if (number) {
                        statNumber.textContent = '0';
                        setTimeout(() => {
                            animateCounter(statNumber, number);
                        }, 500);
                    }
                }
            }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('.stat').forEach(stat => {
        statsObserver.observe(stat);
    });

    // Mouse trail effect
    let mouseTrail = [];
    const maxTrailLength = 20;

    document.addEventListener('mousemove', (e) => {
        mouseTrail.push({ x: e.clientX, y: e.clientY, time: Date.now() });
        
        if (mouseTrail.length > maxTrailLength) {
            mouseTrail.shift();
        }
        
        // Create trail particles
        if (Math.random() < 0.1) {
            createTrailParticle(e.clientX, e.clientY);
        }
    });

    function createTrailParticle(x, y) {
        const particle = document.createElement('div');
        particle.style.cssText = `
            position: fixed;
            width: 4px;
            height: 4px;
            background: var(--primary);
            border-radius: 50%;
            pointer-events: none;
            z-index: 9999;
            left: ${x}px;
            top: ${y}px;
            animation: particleFade 1s ease-out forwards;
        `;
        
        document.body.appendChild(particle);
        
        setTimeout(() => {
            particle.remove();
        }, 1000);
    }

    // Page transition effects
    const pageTransition = () => {
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--gradient);
            z-index: 10000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        `;
        
        document.body.appendChild(overlay);
        
        setTimeout(() => {
            overlay.style.opacity = '1';
        }, 10);
        
        setTimeout(() => {
            overlay.style.opacity = '0';
            setTimeout(() => {
                overlay.remove();
            }, 300);
        }, 500);
    };

    // Add page transition to navigation links
    document.querySelectorAll('a[href^="/"]').forEach(link => {
        link.addEventListener('click', (e) => {
            if (!e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                pageTransition();
                setTimeout(() => {
                    window.location.href = link.href;
                }, 300);
            }
        });
    });
});

// Enhanced utility functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Enhanced notification styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-xl);
        padding: var(--space-4);
        box-shadow: var(--shadow-glow);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: var(--space-3);
        min-width: 300px;
        max-width: 500px;
        animation: slideInRight 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        backdrop-filter: blur(20px);
    `;
    
    // Type-specific styling
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#06b6d4'
    };
    
    notification.style.borderLeftColor = colors[type] || colors.info;
    notification.style.borderLeftWidth = '4px';
    
    document.body.appendChild(notification);
    
    // Auto remove with fade out
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease-in forwards';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
    
    // Add click to dismiss
    notification.addEventListener('click', () => {
        notification.style.animation = 'slideOutRight 0.3s ease-in forwards';
        setTimeout(() => notification.remove(), 300);
    });
}

function getNotificationIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'error': return 'exclamation-circle';
        case 'warning': return 'exclamation-triangle';
        default: return 'info-circle';
    }
}

// Loading overlay utility
function showLoadingOverlay(message = 'Loading...') {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.innerHTML = `
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <p>${message}</p>
        </div>
    `;
    
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(15, 15, 35, 0.9);
        backdrop-filter: blur(10px);
        z-index: 10001;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.3s ease;
    `;
    
    document.body.appendChild(overlay);
    return overlay;
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => overlay.remove(), 300);
    }
}

// Enhanced CSS animations
const enhancedStyle = document.createElement('style');
enhancedStyle.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    @keyframes slideInLeft {
        from {
            transform: translateX(-100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    
    @keyframes ripple {
        to {
            transform: scale(2);
            opacity: 0;
        }
    }
    
    @keyframes particleFade {
        0% {
            opacity: 1;
            transform: scale(1);
        }
        100% {
            opacity: 0;
            transform: scale(0) translateY(-20px);
        }
    }
    
    @keyframes targetBounce {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: var(--space-2);
        flex: 1;
    }
    
    .notification-close {
        background: none;
        border: none;
        color: var(--text-secondary);
        cursor: pointer;
        padding: var(--space-1);
        border-radius: var(--radius-sm);
        transition: var(--transition);
    }
    
    .notification-close:hover {
        background: var(--background);
        color: var(--text-primary);
        transform: scale(1.1);
    }
    
    .loading-content {
        text-align: center;
        color: var(--text-primary);
    }
    
    .loading-spinner {
        width: 50px;
        height: 50px;
        border: 4px solid rgba(139, 92, 246, 0.3);
        border-radius: 50%;
        border-top-color: var(--primary);
        animation: spin 1s linear infinite;
        margin: 0 auto var(--space-4);
    }
    
    .animate-in {
        animation: bounceIn 0.6s ease-out;
    }
    
    @keyframes bounceIn {
        0% {
            opacity: 0;
            transform: scale(0.3) translateY(50px);
        }
        50% {
            opacity: 1;
            transform: scale(1.05) translateY(-10px);
        }
        70% {
            transform: scale(0.9) translateY(0px);
        }
        100% {
            opacity: 1;
            transform: scale(1) translateY(0px);
        }
    }
`;
document.head.appendChild(enhancedStyle);

// Export enhanced utilities
window.FinAnalyzer = {
    showNotification,
    showLoadingOverlay,
    hideLoadingOverlay
};