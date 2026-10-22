/** @odoo-module **/

(function () {
    'use strict';

    // Helper: Gửi JSON-RPC request tới Odoo controller
    async function jsonRpc(url, params) {
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: params || {},
                    id: Math.floor(Math.random() * 1000000),
                }),
            });
            const data = await res.json();
            return data.result || {};
        } catch (err) {
            console.error('BeautyMatch Wishlist JSON-RPC Error:', err);
            return {};
        }
    }

    // Hiển thị thông báo Toast mượt mà ở góc màn hình
    function showWishlistToast(message, isAdded) {
        let toastEl = document.getElementById('bm_wishlist_toast');
        if (!toastEl) {
            toastEl = document.createElement('div');
            toastEl.id = 'bm_wishlist_toast';
            toastEl.style.cssText = `
                position: fixed;
                bottom: 24px;
                right: 24px;
                background: #FFFFFF;
                color: #2B2430;
                border-radius: 14px;
                padding: 12px 20px;
                box-shadow: 0 10px 30px rgba(110, 76, 126, 0.22);
                border: 1px solid #ECE3F2;
                z-index: 99999;
                display: flex;
                align-items: center;
                gap: 12px;
                font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
                font-size: 0.92rem;
                font-weight: 500;
                transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                opacity: 0;
                transform: translateY(16px);
                pointer-events: none;
            `;
            document.body.appendChild(toastEl);
        }

        const iconHtml = isAdded
            ? '<i class="fa fa-heart text-danger fa-lg" style="animation: bmHeartPop 0.3s ease;"></i>'
            : '<i class="fa fa-heart-o text-muted fa-lg"></i>';
        toastEl.innerHTML = `${iconHtml}<span>${message}</span>`;
        toastEl.style.opacity = '1';
        toastEl.style.transform = 'translateY(0)';

        clearTimeout(toastEl._timer);
        toastEl._timer = setTimeout(() => {
            toastEl.style.opacity = '0';
            toastEl.style.transform = 'translateY(16px)';
        }, 3000);
    }

    // Cập nhật số lượng trên icon Wishlist ở Header
    function updateHeaderWishlistBadge(count) {
        const badges = document.querySelectorAll('.my_wish_quantity');
        badges.forEach(badge => {
            badge.textContent = count;
            if (count > 0) {
                badge.classList.remove('d-none');
            } else {
                badge.classList.add('d-none');
            }
        });

        // Đồng bộ sessionStorage native của Odoo nếu có
        try {
            const el = document.querySelector('.o_wsale_my_wish_hide_empty');
            if (el) {
                el.classList.toggle('d-none', count === 0);
            }
        } catch (e) {}
    }

    // Xử lý sự kiện click toggle wishlist
    async function handleWishlistToggle(btn) {
        if (btn.classList.contains('is-loading')) return;
        btn.classList.add('is-loading');

        const form = btn.closest('form') || document.querySelector('form.js_add_cart_variants');
        let productId = btn.dataset.productProductId || btn.dataset.productId;
        if (form && (!productId || form.querySelector('input[name="product_id"]'))) {
            const pInput = form.querySelector('input[name="product_id"]');
            if (pInput && pInput.value) {
                productId = pInput.value;
            }
        }
        const productTmplId = btn.dataset.productTemplateId;

        const res = await jsonRpc('/shop/wishlist/toggle', {
            product_id: productId ? parseInt(productId) : false,
            product_template_id: productTmplId ? parseInt(productTmplId) : false,
        });

        btn.classList.remove('is-loading');

        if (!res || !res.action) {
            return;
        }

        const isAdded = res.action === 'added';
        const targetTmplId = res.product_tmpl_id || productTmplId;

        // Cập nhật tất cả các nút tương ứng với product_template_id này trên trang
        const matchingList = Array.from(document.querySelectorAll(
            `.js_bm_wishlist_toggle[data-product-template-id="${targetTmplId}"]`
        ));
        const btnsToUpdate = Array.from(new Set([btn, ...matchingList]));

        btnsToUpdate.forEach(el => {
            el.dataset.inWish = isAdded ? '1' : '0';
            const icon = el.querySelector('.fa');
            const textSpan = el.querySelector('.js_bm_wishlist_text');

            if (isAdded) {
                el.classList.add('o_in_wishlist', 'text-danger');
                if (el.classList.contains('bm-detail-wishlist-btn')) {
                    el.classList.add('border-danger');
                }
                if (icon) {
                    icon.classList.remove('fa-heart-o');
                    icon.classList.add('fa-heart', 'text-danger');
                }
                if (textSpan) {
                    textSpan.textContent = 'Đã yêu thích';
                }
                // Animation pop nhẹ
                el.style.transform = 'scale(1.18)';
                setTimeout(() => { el.style.transform = ''; }, 220);
            } else {
                el.classList.remove('o_in_wishlist', 'text-danger', 'border-danger');
                if (icon) {
                    icon.classList.remove('fa-heart', 'text-danger');
                    icon.classList.add('fa-heart-o');
                }
                if (textSpan) {
                    textSpan.textContent = 'Yêu thích';
                }
            }
        });

        // Cập nhật số lượng trên Header
        if (typeof res.count !== 'undefined') {
            updateHeaderWishlistBadge(res.count);
        }

        // Thông báo Toast
        const productName = res.product_name || 'Sản phẩm';
        if (isAdded) {
            showWishlistToast(`Đã thêm "${productName}" vào yêu thích!`, true);
        } else {
            showWishlistToast(`Đã bỏ "${productName}" khỏi yêu thích!`, false);
        }
    }

    // Đăng ký event delegation trực tiếp trên document (không phụ thuộc thời điểm DOMContentLoaded)
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.js_bm_wishlist_toggle');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            handleWishlistToggle(btn);
        }
    });

    // Hàm dùng chung: Thêm giỏ hàng nhanh (AJAX) không reload trang, cập nhật header badge và toast
    async function executeQuickAddToCart(btn, productId, form) {
        if (!productId && form) {
            productId = form.querySelector('[name="product_id"]')?.value;
        }
        if (!productId) return;

        const originalHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i> Đang thêm...';
        }

        try {
            const formData = form ? new FormData(form) : new FormData();
            if (!formData.has('product_id')) {
                formData.append('product_id', productId);
            }
            formData.append('ajax', '1');

            const response = await fetch('/beautymatch/cart/add', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData,
            });

            const data = await response.json();
            if (data && data.status === 'success') {
                if (btn) {
                    btn.innerHTML = '<i class="fa fa-check me-1"></i> Đã thêm!';
                    btn.style.backgroundColor = '#2E7D32';
                }

                // Cập nhật số lượng giỏ hàng trên header
                const cartBadges = document.querySelectorAll('.my_cart_quantity');
                cartBadges.forEach(badge => {
                    badge.textContent = data.cart_quantity;
                    badge.classList.remove('d-none');
                });

                showWishlistToast(`Đã thêm "${data.product_name || 'sản phẩm'}" vào giỏ hàng!`, true);

                setTimeout(() => {
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = originalHtml;
                        btn.style.backgroundColor = '';
                    }
                }, 1600);
            } else {
                window.location.href = '/shop/cart';
            }
        } catch (err) {
            console.warn('AJAX cart add fallback:', err);
            if (form) {
                form.submit();
            } else {
                window.location.href = `/beautymatch/cart/add?product_id=${productId}`;
            }
        }
    }

    // 1. Lắng nghe Submit form trên toàn bộ thẻ sản phẩm
    document.addEventListener('submit', function (e) {
        const form = e.target.closest('.js_bm_cart_form');
        if (!form) return;

        e.preventDefault();
        e.stopPropagation();

        const btn = form.querySelector('.bm-btn-addtocart, .js_bm_quick_add_cart');
        const pId = form.querySelector('[name="product_id"]')?.value || (btn && btn.dataset.productId);
        executeQuickAddToCart(btn, pId, form);
    });

    // 2. Lắng nghe Click trực tiếp trên bất kỳ nút Thêm giỏ hàng nào (cửa hàng, trang so sánh, v.v.)
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.bm-btn-addtocart, .js_bm_quick_add_cart');
        if (!btn) return;

        const form = btn.closest('.js_bm_cart_form');
        // Nếu nút nằm trong form, event submit sẽ tự kích hoạt, chỉ xử lý click trực tiếp nếu không nằm trong form hoặc button type="button"
        if (!form || btn.type === 'button') {
            e.preventDefault();
            e.stopPropagation();
            const pId = btn.dataset.productId || (form && form.querySelector('[name="product_id"]')?.value);
            executeQuickAddToCart(btn, pId, form);
        }
    });
})();
