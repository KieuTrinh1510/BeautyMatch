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
        if (!stockBadge) return;

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
            const thresholdEl = document.querySelector('#threshold_message');
            let badgeClass = 'badge bg-success-subtle text-success border border-success-subtle px-2 py-1 rounded-pill small';
            let iconHtml = '<i class="fa fa-check-circle me-1"></i>';
            let textHtml = 'Còn hàng';

            if (thresholdEl && thresholdEl.textContent.trim()) {
                const match = thresholdEl.textContent.match(/\d+/);
                if (match) {
                    const qty = parseInt(match[0], 10);
                    if (qty <= 5) {
                        badgeClass = 'badge bg-warning-subtle text-dark border border-warning-subtle px-2 py-1 rounded-pill small';
                        iconHtml = '<i class="fa fa-fire text-danger me-1"></i>';
                        textHtml = `Chỉ còn <strong class="text-danger">${qty}</strong> sản phẩm`;
                    } else {
                        textHtml = `Còn hàng (${qty} sản phẩm)`;
                    }
                }
            } else {
                const currentText = stockText ? stockText.textContent.trim() : '';
                if (currentText.includes('sản phẩm')) {
                    textHtml = currentText;
                    if (currentText.includes('Chỉ còn')) {
                        badgeClass = 'badge bg-warning-subtle text-dark border border-warning-subtle px-2 py-1 rounded-pill small';
                        iconHtml = '<i class="fa fa-fire text-danger me-1"></i>';
                    }
                }
            }

            stockBadge.className = badgeClass;
            stockBadge.innerHTML = `${iconHtml}<span id="bm_stock_status_text">${textHtml}</span>`;

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

    // ========================================================
    // 3. XỬ LÝ NÚT "MUA NGAY" -> VÀO THẲNG TRANG THANH TOÁN (/shop/payment)
    // ========================================================
    let isSubmittingBuyNow = false;

    document.addEventListener('click', async (ev) => {
        const buyNowBtn = ev.target.closest('.o_we_buy_now');
        if (!buyNowBtn) return;

        // Chặn hoàn toàn hành vi mặc định và handler của Odoo (Odoo native chuyển sang /shop/cart)
        ev.preventDefault();
        ev.stopPropagation();
        ev.stopImmediatePropagation();

        if (isSubmittingBuyNow) return;
        if (buyNowBtn.classList.contains('disabled') || buyNowBtn.getAttribute('disabled')) {
            return;
        }

        const form = buyNowBtn.closest('form') ||
                     document.querySelector('form.js_add_cart_variants') ||
                     document.querySelector('#product_detail form');

        let productId = null;
        let quantity = 1;

        if (form) {
            const prodInput = form.querySelector('input[name="product_id"]');
            if (prodInput && prodInput.value) {
                productId = parseInt(prodInput.value, 10);
            }
            const qtyInput = form.querySelector('input[name="add_qty"], input.quantity');
            if (qtyInput && qtyInput.value) {
                quantity = parseFloat(qtyInput.value) || 1;
            }
        }

        if (!productId) {
            const prodInput = document.querySelector('input[name="product_id"]');
            if (prodInput && prodInput.value) {
                productId = parseInt(prodInput.value, 10);
            }
        }

        if (!productId) {
            console.warn('[BeautyMatch] Không tìm thấy product_id');
            return;
        }

        isSubmittingBuyNow = true;
        const originalContent = buyNowBtn.innerHTML;
        buyNowBtn.classList.add('disabled');
        buyNowBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Đang đến trang thanh toán...';

        try {
            const response = await fetch('/shop/cart/buy_now', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        product_id: productId,
                        quantity: quantity,
                    },
                }),
            });

            const data = await response.json();
            const result = data.result || {};

            if (result.status === 'success' && result.redirect_url) {
                window.location.href = result.redirect_url;
            } else if (result.redirect_url) {
                window.location.href = result.redirect_url;
            } else {
                window.location.href = '/shop/payment';
            }
        } catch (err) {
            console.error('[BeautyMatch] Lỗi khi xử lý Mua ngay:', err);
            window.location.href = '/shop/payment';
        } finally {
            setTimeout(() => {
                isSubmittingBuyNow = false;
                if (buyNowBtn) {
                    buyNowBtn.classList.remove('disabled');
                    buyNowBtn.innerHTML = originalContent;
                }
            }, 4000);
        }
    }, true); // useCapture = true: bắt sự kiện trước khi bubble tới Odoo interactions
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProductDetail);
} else {
    initProductDetail();
}
