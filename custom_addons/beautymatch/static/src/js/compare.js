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
                credentials: 'same-origin',
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

    // Show toast message (tạo động nếu DOM chưa có)
    function showToast(message) {
        let toastEl = document.getElementById('bm_compare_toast');
        if (!toastEl) {
            toastEl = document.createElement('div');
            toastEl.id = 'bm_compare_toast';
            toastEl.className = 'position-fixed top-0 start-50 translate-middle-x p-3';
            toastEl.style.zIndex = '10000';
            toastEl.innerHTML = `
                <div class="toast show bg-danger text-white border-0 rounded-4 shadow-lg p-2" role="alert">
                    <div class="d-flex align-items-center">
                        <i class="fa fa-exclamation-triangle fa-lg me-2 ms-2"></i>
                        <div class="toast-body fw-medium py-2"></div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="document.getElementById('bm_compare_toast').style.display='none'"></button>
                    </div>
                </div>
            `;
            document.body.appendChild(toastEl);
        }
        const body = toastEl.querySelector('.toast-body');
        if (body && message) {
            body.textContent = message;
        }
        toastEl.style.display = 'block';
        clearTimeout(toastEl._timer);
        toastEl._timer = setTimeout(() => {
            toastEl.style.display = 'none';
        }, 3500);
    }

    // Render floating compare bar items (tạo động nếu layout chưa mount)
    function renderCompareBar(data) {
        if (!data) return;
        let barEl = document.getElementById('bm_floating_compare_bar');
        let countLabel = document.getElementById('bm_compare_count_label');
        let container = document.getElementById('bm_compare_items_container');

        if (!barEl) {
            barEl = document.createElement('div');
            barEl.id = 'bm_floating_compare_bar';
            barEl.className = 'bm-floating-compare-bar position-fixed bottom-0 start-0 end-0 bg-white border-top shadow-lg py-2 px-3';
            barEl.style.cssText = 'z-index: 9999; display: none; transition: transform 0.3s ease;';
            barEl.innerHTML = `
                <div class="container d-flex align-items-center justify-content-between flex-wrap gap-2">
                    <div class="d-flex align-items-center gap-3">
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-circle p-2 d-flex align-items-center justify-content-center" style="background-color: #F3ECF8; color: #6E4C7E; width: 36px; height: 36px;">
                                <i class="fa fa-exchange"></i>
                            </span>
                            <div>
                                <strong class="d-block text-dark small">So sánh sản phẩm</strong>
                                <small class="text-muted" id="bm_compare_count_label">0/3 sản phẩm đã chọn</small>
                            </div>
                        </div>
                        <div class="d-flex align-items-center gap-2 flex-wrap" id="bm_compare_items_container"></div>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <button type="button" class="btn btn-sm btn-link text-muted text-decoration-none py-1 px-2" id="bm_compare_clear_btn">
                            <i class="fa fa-trash-o me-1"></i>Xóa tất cả
                        </button>
                        <a href="/compare" class="btn btn-sm text-white rounded-pill px-4 py-2 shadow-sm fw-semibold" style="background-color: #6E4C7E;" id="bm_compare_go_btn">
                            So sánh ngay <i class="fa fa-arrow-right ms-1"></i>
                        </a>
                    </div>
                </div>
            `;
            document.body.appendChild(barEl);
            countLabel = document.getElementById('bm_compare_count_label');
            container = document.getElementById('bm_compare_items_container');
        }

        const count = data.count || 0;
        const products = data.products || [];

        if (countLabel) {
            countLabel.textContent = `${count}/3 sản phẩm đã chọn`;
        }

        if (count === 0) {
            barEl.style.display = 'none';
            if (container) container.innerHTML = '';
        } else {
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

            if (container) container.innerHTML = html;
            barEl.style.display = 'block';

            // Bind remove buttons inside the bar
            container.querySelectorAll('.js_bm_bar_remove_btn').forEach(btn => {
                btn.addEventListener('click', async function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const pId = parseInt(this.dataset.productId);
                    if (pId) await removeProduct(pId);
                });
            });
        }

        // Cập nhật trạng thái tất cả các nút toggle so sánh trên trang
        const productIds = (data.product_ids || []).map(id => parseInt(id));
        document.querySelectorAll('.js_bm_compare_toggle').forEach(btn => {
            const bId = parseInt(btn.dataset.productId);
            const inList = productIds.includes(bId);
            const textSpan = btn.querySelector('.bm-compare-btn-text');

            if (inList) {
                btn.classList.add('active');
                if (btn.classList.contains('bm-card-compare-btn')) {
                    btn.style.backgroundColor = '#F3ECF8';
                    btn.style.color = '#6E4C7E';
                    btn.style.borderColor = '#CDB7DD';
                } else {
                    btn.classList.add('btn-primary', 'text-white');
                    btn.classList.remove('btn-outline-primary');
                }
                if (textSpan) textSpan.textContent = 'Đã thêm so sánh';
            } else {
                btn.classList.remove('active');
                if (btn.classList.contains('bm-card-compare-btn')) {
                    btn.style.backgroundColor = '';
                    btn.style.color = '';
                    btn.style.borderColor = '';
                } else {
                    btn.classList.remove('btn-primary', 'text-white');
                    btn.classList.add('btn-outline-primary');
                }
                if (textSpan) textSpan.textContent = 'So sánh';
            }
        });
    }

    // Toggle product in compare
    async function toggleProduct(productId, clickedBtn) {
        if (!productId) return;
        if (clickedBtn) {
            clickedBtn.style.pointerEvents = 'none';
            clickedBtn.style.opacity = '0.6';
        }
        try {
            const res = await jsonRpc('/shop/compare/toggle', { product_id: productId });
            if (res && res.status === 'limit_exceeded') {
                showToast(res.message || 'Bạn chỉ có thể so sánh tối đa 3 sản phẩm.');
            } else if (res) {
                renderCompareBar(res);
                if (window.location.pathname === '/compare') {
                    window.location.reload();
                }
            }
        } catch (err) {
            console.error('Error toggling compare product:', err);
        } finally {
            if (clickedBtn) {
                clickedBtn.style.pointerEvents = '';
                clickedBtn.style.opacity = '';
            }
        }
    }

    // Remove product from compare
    async function removeProduct(productId) {
        if (!productId) return;
        try {
            const res = await jsonRpc('/shop/compare/remove', { product_id: productId });
            if (res) {
                renderCompareBar(res);
                if (window.location.pathname === '/compare') {
                    window.location.reload();
                }
            }
        } catch (err) {
            console.error('Error removing compare product:', err);
        }
    }

    // Clear all compare
    async function clearAllCompare() {
        try {
            document.cookie = "comparison_product_ids=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        } catch (e) {}
        try {
            const res = await jsonRpc('/shop/compare/clear', {});
            if (res) {
                renderCompareBar(res);
                if (window.location.pathname === '/compare') {
                    window.location.reload();
                }
            }
        } catch (err) {
            console.error('Error clearing compare:', err);
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

    // ========================================================
    // EVENT DELEGATION TRỰC TIẾP TRÊN DOCUMENT (KHÔNG CHỜ DOMContentLoaded)
    // ========================================================
    document.addEventListener('click', function (e) {
        const toggleBtn = e.target.closest('.js_bm_compare_toggle');
        if (toggleBtn) {
            e.preventDefault();
            e.stopPropagation();
            const pId = parseInt(toggleBtn.dataset.productId);
            if (pId) toggleProduct(pId, toggleBtn);
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

    // Khởi tạo trạng thái ban đầu: tải danh sách sản phẩm đang so sánh
    async function initCompare() {
        try {
            document.cookie = "comparison_product_ids=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        } catch (e) {}

        const initialData = await jsonRpc('/shop/compare/get', {});
        renderCompareBar(initialData);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCompare);
    } else {
        initCompare();
    }
})();
