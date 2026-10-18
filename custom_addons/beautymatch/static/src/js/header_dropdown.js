/* ========================================================
   BeautyMatch Header Dropdowns (Hover + Direct Link Click)
   - Hover on menu/caret opens dropdown smoothly
   - Click on main text navigates directly to target URL (/shop, /theo-van-de-da)
   - Dropdown stays open while mouse moves into dropdown menu
   - Automatic close on mouseleave with debounce (180ms)
   - Click outside closes open dropdowns
   - Caret toggle button supported for touch / tablet devices
   ======================================================== */

(function () {
    'use strict';

    function initHeaderDropdowns() {
        const dropdownItems = document.querySelectorAll('.bm-nav-item-dropdown');
        if (!dropdownItems.length) return;

        dropdownItems.forEach(item => {
            const link = item.querySelector('.bm-nav-link');
            const caretBtn = item.querySelector('.bm-caret-btn');
            const menu = item.querySelector('.dropdown-menu');
            let closeTimer = null;

            function openDropdown() {
                if (closeTimer) {
                    clearTimeout(closeTimer);
                    closeTimer = null;
                }
                // Close other dropdowns
                dropdownItems.forEach(other => {
                    if (other !== item) {
                        other.classList.remove('show', 'bm-open');
                        const otherMenu = other.querySelector('.dropdown-menu');
                        if (otherMenu) otherMenu.classList.remove('show');
                        const otherBtn = other.querySelector('.bm-caret-btn');
                        if (otherBtn) otherBtn.setAttribute('aria-expanded', 'false');
                    }
                });

                item.classList.add('show', 'bm-open');
                if (menu) menu.classList.add('show');
                if (caretBtn) caretBtn.setAttribute('aria-expanded', 'true');
            }

            function closeDropdown(delay = 180) {
                if (closeTimer) clearTimeout(closeTimer);
                closeTimer = setTimeout(() => {
                    item.classList.remove('show', 'bm-open');
                    if (menu) menu.classList.remove('show');
                    if (caretBtn) caretBtn.setAttribute('aria-expanded', 'false');
                }, delay);
            }

            // Desktop mouse hover events
            item.addEventListener('mouseenter', openDropdown);
            item.addEventListener('mouseleave', () => closeDropdown(180));

            // Main link click: allow natural navigation to target URL, close dropdown
            if (link) {
                link.addEventListener('click', function () {
                    const href = this.getAttribute('href');
                    if (href && href !== '#') {
                        closeDropdown(0);
                    }
                });
            }

            // Caret button click (toggle for touch/click)
            if (caretBtn) {
                caretBtn.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (item.classList.contains('show') || item.classList.contains('bm-open')) {
                        closeDropdown(0);
                    } else {
                        openDropdown();
                    }
                });
            }

            // Dropdown menu events
            if (menu) {
                menu.addEventListener('mouseenter', openDropdown);
                menu.addEventListener('mouseleave', () => closeDropdown(180));
                menu.querySelectorAll('a').forEach(menuLink => {
                    menuLink.addEventListener('click', () => {
                        closeDropdown(0);
                    });
                });
            }
        });

        // Close when clicking anywhere outside
        document.addEventListener('click', function (e) {
            if (!e.target.closest('.bm-nav-item-dropdown')) {
                dropdownItems.forEach(item => {
                    item.classList.remove('show', 'bm-open');
                    const menu = item.querySelector('.dropdown-menu');
                    if (menu) menu.classList.remove('show');
                    const caretBtn = item.querySelector('.bm-caret-btn');
                    if (caretBtn) caretBtn.setAttribute('aria-expanded', 'false');
                });
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHeaderDropdowns);
    } else {
        initHeaderDropdowns();
    }
})();
