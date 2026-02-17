/**
 * Dark Theme Module
 * Manages light/dark theme toggling with localStorage persistence.
 */
const DarkTheme = (() => {
    const STORAGE_KEY = 'grm-theme';

    function getPreferred() {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) return saved;
        // Default to light theme
        return 'light';
    }

    function apply(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(STORAGE_KEY, theme);
        updateIcon(theme);
    }

    function updateIcon(theme) {
        const icon = document.getElementById('themeToggleIcon');
        if (!icon) return;
        if (theme === 'dark') {
            icon.className = 'fas fa-sun';
        } else {
            icon.className = 'fas fa-moon';
        }
    }

    function toggle() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        apply(current === 'dark' ? 'light' : 'dark');
    }

    function init() {
        apply(getPreferred());
    }

    return { init, toggle };
})();

// Initialize as soon as DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', DarkTheme.init);
} else {
    DarkTheme.init();
}
