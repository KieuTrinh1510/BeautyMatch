/** @odoo-module **/

/* ========================================================
   BeautyMatch Skincare Shop Filters & Range Slider
   ======================================================== */

(function () {
    'use strict';

    function initShopFilters() {
        const filterForms = document.querySelectorAll('#bm_shop_filter_form');
        if (!filterForms.length) return;

        filterForms.forEach(form => {
            const minInput = form.querySelector('input[name="min_price"]');
            const maxInput = form.querySelector('input[name="max_price"]');
            const slider = form.querySelector('.bm-price-range-slider');

            if (slider && maxInput) {
                // When slider moves, sync max price input
                slider.addEventListener('input', function () {
                    maxInput.value = this.value;
                });

                // When max price input changes, sync slider
                maxInput.addEventListener('input', function () {
                    const val = parseInt(this.value, 10);
                    if (!isNaN(val)) {
                        slider.value = Math.min(Math.max(val, 0), 1500000);
                    }
                });
            }

            // Checkbox navigation via data-url
            form.querySelectorAll('.js_bm_filter_checkbox').forEach(cb => {
                cb.addEventListener('change', function () {
                    const targetUrl = this.dataset.url;
                    if (targetUrl) {
                        window.location.href = targetUrl;
                    }
                });
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initShopFilters);
    } else {
        initShopFilters();
    }
})();
