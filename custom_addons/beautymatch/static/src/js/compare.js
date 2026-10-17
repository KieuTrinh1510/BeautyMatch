/** @odoo-module **/

(function () {
    'use strict';

    // Helper: Make JSON-RPC request to Odoo controller
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
            console.error('BeautyMatch JSON-RPC Error:', err);
            return {};
        }
    }

    // Show toast message
    function showToast(message) {
        const toastEl = document.getElementById('bm_compare_toast');
        if (toastEl) {
            const body = toastEl.querySelector('.toast-body');
            if (body && message) {
                body.textContent = message;
            }
            toastEl.style.display = 'block';
            setTimeout(() => {
                toastEl.style.display = 'none';
            }, 3500);
        } else {
            alert(message);
        }
    }

    // Render floating compare bar items
    function renderCompareBar(data) {
        const barEl = document.getElementById('bm_floating_compare_bar');
        const countLabel = document.getElementById('bm_compare_count_label');
        const container = document.getElementById('bm_compare_items_container');
        if (!barEl || !container) return;

        const count = data.count || 0;
        const products = data.products || [];

        if (countLabel) {
            countLabel.textContent = `${count}/3 sản phẩm đã chọn`;
        }

        if (count === 0) {
            barEl.style.display = 'none';
            container.innerHTML = '';
            return;
        }

        // Generate mini cards
        let html = '';
        products.forEach(p => {
            html += `
                <div class="d-flex align-items-center gap-1 bg-light border rounded-pill px-2 py-1 small">
                    <img src="${p.image_url}" alt="${p.name}" style="width: 24px; height: 24px; object-fit: contain; border-radius: 50%; background: white;">
                    <span class="text-truncate text-dark fw-medium" style="max-width: 130px;" title="${p.name}">${p.name}</span>
                    <button type="button" class="btn btn-sm btn-link text-muted p-0 ms-1 js_bm_bar_remove_btn" data-product-id="${p.id}" style="line-height: 1;">
                        <i class="fa fa-times-circle text-danger"></i>
                    </button>
                </div>
            `;
        });

        container.innerHTML = html;
        barEl.style.display = 'block';

        // Bind remove buttons inside the bar
        container.querySelectorAll('.js_bm_bar_remove_btn').forEach(btn => {
            btn.addEventListener('click', async function (e) {
                e.preventDefault();
                e.stopPropagation();
                const pId = parseInt(this.dataset.productId);
                await removeProduct(pId);
            });
        });

        // Update all toggle buttons on page
        const productIds = (data.product_ids || []).map(id => parseInt(id));
        document.querySelectorAll('.js_bm_compare_toggle').forEach(btn => {
            const bId = parseInt(btn.dataset.productId);
            const inList = productIds.includes(bId);
            const textSpan = btn.querySelector('.bm-compare-btn-text');

            if (inList) {
                btn.classList.add('active', 'text-primary', 'border-primary');
                if (textSpan) textSpan.textContent = 'Đã thêm vào so sánh';
            } else {
                btn.classList.remove('active', 'text-primary', 'border-primary');
                if (textSpan) textSpan.textContent = 'So sánh';
            }
        });
    }

    // Toggle product in compare
    async function toggleProduct(productId) {
        const res = await jsonRpc('/shop/compare/toggle', { product_id: productId });
        if (res.status === 'limit_exceeded') {
            showToast(res.message || 'Bạn chỉ có thể so sánh tối đa 3 sản phẩm.');
        } else {
            renderCompareBar(res);
            if (window.location.pathname === '/compare') {
                window.location.reload();
            }
        }
    }

    // Remove product from compare
    async function removeProduct(productId) {
        const res = await jsonRpc('/shop/compare/remove', { product_id: productId });
        renderCompareBar(res);
        if (window.location.pathname === '/compare') {
            window.location.reload();
        }
    }

    // Clear all compare
    async function clearAllCompare() {
        try {
            document.cookie = "comparison_product_ids=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        } catch (e) {}
        const res = await jsonRpc('/shop/compare/clear', {});
        renderCompareBar(res);
        if (window.location.pathname === '/compare') {
            window.location.reload();
        }
    }

    // Quick add to cart
    async function quickAddToCart(variantId, templateId) {
        try {
            await jsonRpc('/shop/cart/add', {
                product_template_id: parseInt(templateId || variantId),
                product_id: parseInt(variantId),
                quantity: 1,
            });
            window.location.href = '/shop/cart';
        } catch (e) {
            window.location.href = '/shop/cart';
        }
    }

    // Initialize listeners
    document.addEventListener('DOMContentLoaded', async function () {
        // Vô hiệu hoá hoàn toàn cookie so sánh native của Odoo
        try {
            document.cookie = "comparison_product_ids=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        } catch (e) {}

        // Fetch current compare state
        const initialData = await jsonRpc('/shop/compare/get', {});
        renderCompareBar(initialData);

        // Click delegation for toggle buttons
        document.addEventListener('click', function (e) {
            const toggleBtn = e.target.closest('.js_bm_compare_toggle');
            if (toggleBtn) {
                e.preventDefault();
                e.stopPropagation();
                const pId = parseInt(toggleBtn.dataset.productId);
                if (pId) toggleProduct(pId);
                return;
            }

            const removeBtn = e.target.closest('.js_bm_compare_remove_btn');
            if (removeBtn) {
                e.preventDefault();
                e.stopPropagation();
                const pId = parseInt(removeBtn.dataset.productId);
                if (pId) removeProduct(pId);
                return;
            }

            const clearBtn = e.target.closest('.js_bm_compare_clear_all, #bm_compare_clear_btn');
            if (clearBtn) {
                e.preventDefault();
                e.stopPropagation();
                clearAllCompare();
                return;
            }

            const cartBtn = e.target.closest('.js_bm_quick_add_cart');
            if (cartBtn) {
                e.preventDefault();
                e.stopPropagation();
                const vId = cartBtn.dataset.productId;
                const tId = cartBtn.dataset.productTemplateId;
                if (vId) quickAddToCart(vId, tId);
                return;
            }
        });
    });
})();
