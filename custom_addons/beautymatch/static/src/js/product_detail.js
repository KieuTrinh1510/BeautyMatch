/** @odoo-module **/

function initProductDetail() {
    // ========================================================
    // 1. SCROLL TỚI REVIEW KHI CÓ ANCHOR #reviews
    // ========================================================
    function handleReviewAnchor() {
        if (window.location.hash === '#reviews') {
            const reviewElem = document.getElementById('reviews');
            if (reviewElem) {
                setTimeout(() => {
                    reviewElem.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    reviewElem.classList.add('shadow-lg');
                    setTimeout(() => reviewElem.classList.remove('shadow-lg'), 2000);
                }, 300);
            }
        }
    }
    handleReviewAnchor();
    window.addEventListener('hashchange', handleReviewAnchor);

    // ========================================================
    // 2. CẬP NHẬT BADGE TỒN KHO & DISABLE NÚT KHI VARIANT THAY ĐỔI
    // ========================================================
    const ctaWrapper = document.getElementById('o_wsale_cta_wrapper');
    const stockBadge = document.getElementById('bm_stock_status_badge');
    const stockText = document.getElementById('bm_stock_status_text');
    const addToCartBtn = document.getElementById('add_to_cart');
    const buyNowBtn = document.querySelector('.o_we_buy_now');

    function updateStockUI(isOutOfStock) {
        if (!stockBadge || !stockText) return;

        if (isOutOfStock) {
            stockBadge.className = 'badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1 rounded-pill small';
            stockBadge.innerHTML = '<i class="fa fa-times-circle me-1"></i><span id="bm_stock_status_text">Hết hàng</span>';
            if (addToCartBtn) {
                addToCartBtn.classList.add('disabled');
                addToCartBtn.setAttribute('disabled', 'disabled');
                addToCartBtn.style.pointerEvents = 'none';
                addToCartBtn.style.opacity = '0.5';
            }
            if (buyNowBtn) {
                buyNowBtn.classList.add('disabled');
                buyNowBtn.setAttribute('disabled', 'disabled');
                buyNowBtn.style.pointerEvents = 'none';
                buyNowBtn.style.opacity = '0.5';
            }
        } else {
            stockBadge.className = 'badge bg-success-subtle text-success border border-success-subtle px-2 py-1 rounded-pill small';
            stockBadge.innerHTML = '<i class="fa fa-check-circle me-1"></i><span id="bm_stock_status_text">Còn hàng</span>';
            if (addToCartBtn) {
                addToCartBtn.classList.remove('disabled');
                addToCartBtn.removeAttribute('disabled');
                addToCartBtn.style.pointerEvents = '';
                addToCartBtn.style.opacity = '';
            }
            if (buyNowBtn) {
                buyNowBtn.classList.remove('disabled');
                buyNowBtn.removeAttribute('disabled');
                buyNowBtn.style.pointerEvents = '';
                buyNowBtn.style.opacity = '';
            }
        }
    }

    if (ctaWrapper) {
        // Observer quan sát thay đổi class của ctaWrapper từ Odoo native website_sale_stock
        const observer = new MutationObserver(() => {
            const isOutOfStock = ctaWrapper.classList.contains('out_of_stock') ||
                                 ctaWrapper.classList.contains('d-none') ||
                                 Boolean(document.querySelector('#out_of_stock_message'));
            updateStockUI(isOutOfStock);
        });

        observer.observe(ctaWrapper, { attributes: true, attributeFilter: ['class', 'style'] });

        // Quan sát thêm container availability_messages
        const availMsgContainer = document.querySelector('.availability_messages');
        if (availMsgContainer) {
            const availObserver = new MutationObserver(() => {
                const isOutOfStock = ctaWrapper.classList.contains('out_of_stock') ||
                                     ctaWrapper.classList.contains('d-none') ||
                                     Boolean(document.querySelector('#out_of_stock_message'));
                updateStockUI(isOutOfStock);
            });
            availObserver.observe(availMsgContainer, { childList: true, subtree: true });
        }

        // Kiểm tra ban đầu khi load trang
        const initialOutOfStock = ctaWrapper.classList.contains('out_of_stock') ||
                                 ctaWrapper.classList.contains('d-none') ||
                                 Boolean(document.querySelector('#out_of_stock_message'));
        if (initialOutOfStock) {
            updateStockUI(true);
        }
    }

    // Lắng nghe sự kiện change trên các radio/select variant
    document.querySelectorAll('.js_product input[type="radio"], .js_product select').forEach(input => {
        input.addEventListener('change', () => {
            setTimeout(() => {
                if (ctaWrapper) {
                    const isOutOfStock = ctaWrapper.classList.contains('out_of_stock') ||
                                         ctaWrapper.classList.contains('d-none') ||
                                         Boolean(document.querySelector('#out_of_stock_message'));
                    updateStockUI(isOutOfStock);
                }
            }, 200);
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProductDetail);
} else {
    initProductDetail();
}
