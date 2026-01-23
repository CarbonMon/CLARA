// Common JavaScript functions for the application

// Theme management
const Theme = {
    dark: "dark",
    light: "light",
    auto: "auto"
};

const THEME_LOCAL_STORAGE_KEY = "clara/theme";

function isAutoTheme(theme) {
    return theme === "auto";
}

function getSystemTheme() {
    if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    return "light";
}

function getInitialTheme() {
    if (typeof window !== "undefined") {
        const rawTheme = window.localStorage.getItem(THEME_LOCAL_STORAGE_KEY);
        if (rawTheme && Object.values(Theme).includes(rawTheme)) {
            return rawTheme;
        }
    }
    return "auto";
}

function applyThemeAttributes(theme) {
    const themeToApply = isAutoTheme(theme) ? getSystemTheme() : theme;
    const htmlTag = document.documentElement;
    htmlTag.classList.remove("dark", "light");
    htmlTag.classList.add(themeToApply);
    htmlTag.setAttribute("data-theme", themeToApply);
    htmlTag.style.colorScheme = themeToApply;
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing theme...');
    
    // Initialize theme
    applyThemeAttributes(getInitialTheme());

    // Theme toggle functionality
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    if (themeToggle) {
        console.log('Theme toggle button found, adding event listener');
        themeToggle.addEventListener('click', function() {
            console.log('Theme toggle clicked');
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            console.log('Current theme:', currentTheme);
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            console.log('New theme:', newTheme);
            applyThemeAttributes(newTheme);
            window.localStorage.setItem(THEME_LOCAL_STORAGE_KEY, newTheme);
            updateThemeIcon(newTheme);
        });

        // Update icon based on current theme
        function updateThemeIcon(theme) {
            if (themeIcon) {
                themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
            }
        }

        // Initial icon update
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        updateThemeIcon(currentTheme);
    } else {
        console.error('Theme toggle button not found');
    }

    // Enable tooltips everywhere
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Add animation when scrolling into view
    function animateOnScroll() {
        const elements = document.querySelectorAll('.animate-on-scroll');
        
        elements.forEach(element => {
            const position = element.getBoundingClientRect();
            
            // Check if element is in viewport
            if(position.top < window.innerHeight && position.bottom >= 0) {
                element.classList.add('animate__animated', element.dataset.animation || 'animate__fadeIn');
            }
        });
    }
    
    // Listen for scroll events
    window.addEventListener('scroll', animateOnScroll);
    
    // Initial check for animations
    animateOnScroll();
    
    // Handle API provider selection
    const apiProviderSelect = document.getElementById('api_provider');
    if (apiProviderSelect) {
        apiProviderSelect.addEventListener('change', function() {
            // This is now handled in the page-specific script in settings.html
        });
    }
    
    // Handle form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

// Format date as YYYY-MM-DD
function formatDate(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
}

// Format number with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Create and show toast notification
        const toastEl = document.createElement('div');
        toastEl.className = 'toast position-fixed bottom-0 end-0 m-3';
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        toastEl.innerHTML = `
            <div class="toast-header bg-success text-white">
                <i class="fas fa-check-circle me-2"></i>
                <strong class="me-auto">Success</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                Text copied to clipboard
            </div>
        `;
        
        document.body.appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        
        // Remove toast after it's hidden
        toastEl.addEventListener('hidden.bs.toast', function() {
            document.body.removeChild(toastEl);
        });
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
    });
}
