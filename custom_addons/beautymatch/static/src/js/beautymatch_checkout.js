/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

/**
 * Quản lý tương tác chọn sản phẩm trong giỏ hàng (/shop/cart) - Shopee Style
 */
export class BeautyMatchCart extends Interaction {
    static selector = "#shop_cart";

    dynamicContent = {
        "#bm_select_all_cart": {
            "t-on-change": this.onSelectAllChange,
        },
        ".bm-cart-line-checkbox": {
            "t-on-change": this.onLineCheckboxChange,
        },
        "#bm_btn_cart_checkout": {
            "t-on-click": this.onCheckoutClick,
        },
    };

    setup() {
        this.syncCartUI();
    }

    start() {
        this.syncCartUI();
    }

    async onSelectAllChange(ev) {
        const isChecked = ev.target.checked;
        const itemCheckboxes = this.el.querySelectorAll(".bm-cart-line-checkbox");
        itemCheckboxes.forEach((cb) => {
            cb.checked = isChecked;
        });
        this.syncCartUI();
        if (!isChecked) {
            this.setCartFormattedTotals("0 ₫", "0 ₫", "0 ₫");
        }
        try {
            const res = await this.waitFor(rpc("/shop/cart/update_selection", { select_all: isChecked }));
            this.applyServerResponse(res);
        } catch (err) {
            console.error("Lỗi cập nhật chọn tất cả:", err);
        }
    }

    async onLineCheckboxChange(ev) {
        const lineCb = ev.target;
        const lineId = lineCb.getAttribute("data-line-id");
        const isChecked = lineCb.checked;
        this.syncCartUI();
        const checkedBoxes = this.el.querySelectorAll(".bm-cart-line-checkbox:checked");
        if (checkedBoxes.length === 0) {
            this.setCartFormattedTotals("0 ₫", "0 ₫", "0 ₫");
        }
        try {
            const res = await this.waitFor(rpc("/shop/cart/update_selection", {
                line_id: lineId,
                selected: isChecked,
            }));
            this.applyServerResponse(res);
        } catch (err) {
            console.error("Lỗi cập nhật chọn sản phẩm:", err);
        }
    }

    onCheckoutClick(ev) {
        const checkedCount = this.el.querySelectorAll(".bm-cart-line-checkbox:checked").length;
        const btn = ev.currentTarget;
        const dataCount = parseInt(btn.getAttribute("data-selected-count") || "0", 10);
        if (btn.classList.contains("disabled") || checkedCount === 0 || dataCount === 0) {
            ev.preventDefault();
            ev.stopPropagation();
            alert("Vui lòng chọn ít nhất 1 sản phẩm để thanh toán.");
        }
    }

    syncCartUI() {
        const itemCheckboxes = this.el.querySelectorAll(".bm-cart-line-checkbox");
        if (!itemCheckboxes.length) return;

        const checkedBoxes = this.el.querySelectorAll(".bm-cart-line-checkbox:checked");
        const totalCount = itemCheckboxes.length;
        const selectedCount = checkedBoxes.length;

        const selectAllCheckbox = this.el.querySelector("#bm_select_all_cart");
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = (totalCount > 0 && selectedCount === totalCount);
        }

        const totalCountSpan = this.el.querySelector("#bm_cart_total_count");
        if (totalCountSpan) totalCountSpan.textContent = totalCount;

        const selectedCountBadge = this.el.querySelector("#bm_cart_selected_count");
        if (selectedCountBadge) selectedCountBadge.textContent = selectedCount;

        const btnCheckoutCount = document.getElementById("bm_btn_checkout_count") || this.el.querySelector("#bm_btn_checkout_count");
        if (btnCheckoutCount) btnCheckoutCount.textContent = selectedCount;

        const checkoutBtn = document.getElementById("bm_btn_cart_checkout") || this.el.querySelector("#bm_btn_cart_checkout");
        if (checkoutBtn) {
            checkoutBtn.setAttribute("data-selected-count", selectedCount);
            if (selectedCount === 0) {
                checkoutBtn.classList.add("disabled");
                checkoutBtn.setAttribute("aria-disabled", "true");
            } else {
                checkoutBtn.classList.remove("disabled");
                checkoutBtn.removeAttribute("aria-disabled");
            }
        }

        if (selectedCount === 0) {
            this.setCartFormattedTotals("0 ₫", "0 ₫", "0 ₫");
        }
    }

    setCartFormattedTotals(subtotal, total, tax) {
        const amountUntaxedSpan = document.getElementById("bm_cart_amount_untaxed");
        const amountTotalSpan = document.getElementById("bm_cart_amount_total");
        const amountTaxSpan = document.getElementById("bm_cart_amount_tax");
        if (amountUntaxedSpan && subtotal) amountUntaxedSpan.textContent = subtotal;
        if (amountTotalSpan && total) amountTotalSpan.textContent = total;
        if (amountTaxSpan && tax) amountTaxSpan.textContent = tax;
    }

    applyServerResponse(res) {
        if (!res || !res.success) return;
        const selectedCountBadge = this.el.querySelector("#bm_cart_selected_count");
        const btnCheckoutCount = document.getElementById("bm_btn_checkout_count") || this.el.querySelector("#bm_btn_checkout_count");
        const totalCountSpan = this.el.querySelector("#bm_cart_total_count");
        const selectAllCheckbox = this.el.querySelector("#bm_select_all_cart");
        const checkoutBtn = document.getElementById("bm_btn_cart_checkout") || this.el.querySelector("#bm_btn_cart_checkout");

        if (selectedCountBadge) selectedCountBadge.textContent = res.selected_count;
        if (btnCheckoutCount) btnCheckoutCount.textContent = res.selected_count;
        if (totalCountSpan && typeof res.total_count !== "undefined") totalCountSpan.textContent = res.total_count;

        if (selectAllCheckbox && typeof res.all_selected !== "undefined") {
            selectAllCheckbox.checked = res.all_selected;
        }

        if (checkoutBtn) {
            checkoutBtn.setAttribute("data-selected-count", res.selected_count);
            if (res.selected_count === 0) {
                checkoutBtn.classList.add("disabled");
                checkoutBtn.setAttribute("aria-disabled", "true");
            } else {
                checkoutBtn.classList.remove("disabled");
                checkoutBtn.removeAttribute("aria-disabled");
            }
        }

        this.setCartFormattedTotals(
            res.selected_subtotal_formatted,
            res.selected_total_formatted,
            res.selected_tax_formatted
        );
    }
}

registry.category("public.interactions").add("beautymatch.cart_interaction", BeautyMatchCart);

/**
 * Quản lý tương tác trang thanh toán (/shop/payment) - Shopee Style
 */
export class BeautyMatchCheckout extends Interaction {
    static selector = "#bm_checkout_shopee_wrapper";

    setup() {
        this.initVoucher();
        this.initAddress();
        this.initDelivery();
    }

    initVoucher() {
        const voucherTickets = this.el.querySelectorAll(".bm-voucher-ticket");
        const voucherRadios = this.el.querySelectorAll(".bm-radio-voucher");
        const clearVoucherBtn = this.el.querySelector("#bm_btn_clear_voucher");

        let anyApplied = false;
        voucherRadios.forEach((radio) => {
            if (radio.checked) {
                anyApplied = true;
            }
        });
        if (clearVoucherBtn) {
            if (anyApplied) {
                clearVoucherBtn.classList.remove("d-none");
            } else {
                clearVoucherBtn.classList.add("d-none");
            }
        }

        voucherTickets.forEach((ticket) => {
            ticket.addEventListener("click", async (e) => {
                if (ticket.classList.contains("disabled")) return;
                const radio = ticket.querySelector(".bm-radio-voucher");
                if (!radio || radio.disabled) return;
                if (e.target === radio) return;

                if (radio.checked) {
                    radio.checked = false;
                    await this.applyVoucher("NONE");
                    return;
                }
                radio.checked = true;
                await this.applyVoucher(radio.value);
            });
        });

        voucherRadios.forEach((radio) => {
            radio.addEventListener("change", async (e) => {
                await this.applyVoucher(e.target.value);
            });
        });

        if (clearVoucherBtn) {
            clearVoucherBtn.addEventListener("click", async (e) => {
                e.preventDefault();
                await this.applyVoucher("NONE");
            });
        }
    }

    async applyVoucher(code) {
        const alertBox = document.getElementById("bm_voucher_alert_msg");
        if (alertBox) {
            alertBox.innerHTML = `
                <div class="alert alert-info py-2 px-3 small rounded-3 mb-0 d-flex align-items-center">
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Đang xử lý ưu đãi...
                </div>
            `;
        }

        try {
            const res = await this.waitFor(rpc("/shop/beautymatch/apply_voucher", { code: code }));
            if (res && res.error) {
                if (alertBox) {
                    alertBox.innerHTML = `
                        <div class="alert alert-danger py-2 px-3 small rounded-3 mb-0">
                            <i class="fa fa-exclamation-circle me-1"></i>${res.error}
                        </div>
                    `;
                }
                setTimeout(() => {
                    window.location.reload();
                }, 1200);
            } else {
                window.location.reload();
            }
        } catch (err) {
            console.error("Lỗi áp dụng voucher:", err);
            if (alertBox) {
                alertBox.innerHTML = `
                    <div class="alert alert-danger py-2 px-3 small rounded-3 mb-0">
                        <i class="fa fa-exclamation-circle me-1"></i>Có lỗi xảy ra khi áp dụng voucher. Vui lòng thử lại.
                    </div>
                `;
            }
        }
    }

    initAddress() {
        const addressModal = document.getElementById("bmAddressModal");
        const listView = document.getElementById("bm_address_list_view");
        const formView = document.getElementById("bm_address_form_view");
        const modalTitle = document.getElementById("bm_modal_title");
        const openAddBtn = document.getElementById("bm_btn_open_add_address");
        const addFirstAddrBtn = document.getElementById("bm_btn_add_first_addr");
        const backToListBtn = document.getElementById("bm_btn_back_to_addr_list");
        const cancelFormBtn = document.getElementById("bm_btn_cancel_addr_form");
        const confirmAddrBtn = document.getElementById("bm_btn_confirm_select_addr");
        const saveInlineAddrBtn = document.getElementById("bm_btn_save_inline_address");

        const inputAddressId = document.getElementById("bm_input_address_id");
        const inputName = document.getElementById("bm_input_name");
        const inputPhone = document.getElementById("bm_input_phone");
        const inputStreet = document.getElementById("bm_input_street");
        const inputCity = document.getElementById("bm_input_city");
        const inputEmail = document.getElementById("bm_input_email");
        const inputIsDefault = document.getElementById("bm_input_is_default");
        const formViewTitle = document.getElementById("bm_form_view_title");

        function showListView() {
            if (listView) listView.classList.remove("d-none");
            if (formView) formView.classList.add("d-none");
            if (modalTitle) modalTitle.textContent = "Địa chỉ của tôi";
        }

        function showFormView(isEdit = false, data = {}) {
            if (listView) listView.classList.add("d-none");
            if (formView) formView.classList.remove("d-none");

            if (isEdit) {
                if (formViewTitle) formViewTitle.textContent = "Cập nhật địa chỉ";
                if (modalTitle) modalTitle.textContent = "Cập nhật địa chỉ";
                if (inputAddressId) inputAddressId.value = data.id || "";
                if (inputName) inputName.value = data.name || "";
                if (inputPhone) inputPhone.value = data.phone || "";
                if (inputStreet) inputStreet.value = data.street || "";
                if (inputCity) inputCity.value = data.city || "Hà Nội";
                if (inputEmail) inputEmail.value = data.email || "";
                if (inputIsDefault) inputIsDefault.checked = (data.isDefault === "1" || data.isDefault === true);
            } else {
                if (formViewTitle) formViewTitle.textContent = "Địa chỉ mới";
                if (modalTitle) modalTitle.textContent = "Thêm địa chỉ mới";
                if (inputAddressId) inputAddressId.value = "";
                if (inputName) inputName.value = "";
                if (inputPhone) inputPhone.value = "";
                if (inputStreet) inputStreet.value = "";
                if (inputCity) inputCity.value = "Hà Nội";
                if (inputEmail) inputEmail.value = "";
                if (inputIsDefault) inputIsDefault.checked = false;
            }
        }

        if (openAddBtn) openAddBtn.addEventListener("click", () => showFormView(false));
        if (addFirstAddrBtn) addFirstAddrBtn.addEventListener("click", () => showFormView(false));
        if (backToListBtn) backToListBtn.addEventListener("click", () => showListView());
        if (cancelFormBtn) cancelFormBtn.addEventListener("click", () => showListView());

        if (addressModal) {
            addressModal.addEventListener("hidden.bs.modal", () => {
                showListView();
            });
        }

        document.querySelectorAll(".bm-btn-edit-addr").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                showFormView(true, {
                    id: btn.dataset.id,
                    name: btn.dataset.name,
                    phone: btn.dataset.phone,
                    street: btn.dataset.street,
                    city: btn.dataset.city,
                    email: btn.dataset.email,
                    isDefault: btn.dataset.default,
                });
            });
        });

        document.querySelectorAll(".bm-btn-set-default").forEach((btn) => {
            btn.addEventListener("click", async (e) => {
                e.stopPropagation();
                const addrId = btn.dataset.id;
                if (!addrId) return;
                btn.disabled = true;
                btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Đang lưu...`;

                try {
                    const res = await rpc("/shop/beautymatch/set_default_address", { address_id: addrId });
                    if (res && res.success) {
                        window.location.reload();
                    } else {
                        alert((res && res.error) || "Không thể đặt làm địa chỉ mặc định.");
                        btn.disabled = false;
                        btn.innerHTML = `Thiết lập mặc định`;
                    }
                } catch (err) {
                    console.error("Lỗi đặt địa chỉ mặc định:", err);
                    btn.disabled = false;
                    btn.innerHTML = `Thiết lập mặc định`;
                }
            });
        });

        document.querySelectorAll(".bm-address-item-card").forEach((card) => {
            card.addEventListener("click", (e) => {
                if (e.target.closest("button") || e.target.closest("a")) return;
                const radio = card.querySelector(".bm-radio-addr");
                if (radio) {
                    radio.checked = true;
                    document.querySelectorAll(".bm-address-item-card").forEach((c) => {
                        c.classList.remove("border-purple", "bg-purple-subtle-light", "shadow-xs");
                        c.classList.add("bg-white");
                    });
                    card.classList.add("border-purple", "bg-purple-subtle-light", "shadow-xs");
                    card.classList.remove("bg-white");
                }
            });
        });

        if (confirmAddrBtn) {
            confirmAddrBtn.addEventListener("click", async () => {
                const checkedRadio = document.querySelector("input[name='bm_selected_partner_id']:checked");
                if (!checkedRadio) {
                    alert("Vui lòng chọn một địa chỉ nhận hàng.");
                    return;
                }
                confirmAddrBtn.disabled = true;
                confirmAddrBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Đang áp dụng...`;

                try {
                    const res = await rpc("/shop/beautymatch/update_shipping_address", {
                        partner_id: checkedRadio.value,
                    });
                    if (res && res.success) {
                        window.location.reload();
                    } else {
                        alert((res && res.error) || "Không thể đổi địa chỉ.");
                        confirmAddrBtn.disabled = false;
                        confirmAddrBtn.innerHTML = `<i class="fa fa-check me-1"></i>Xác nhận`;
                    }
                } catch (err) {
                    console.error("Lỗi áp dụng địa chỉ:", err);
                    confirmAddrBtn.disabled = false;
                    confirmAddrBtn.innerHTML = `<i class="fa fa-check me-1"></i>Xác nhận`;
                }
            });
        }

        if (saveInlineAddrBtn) {
            saveInlineAddrBtn.addEventListener("click", async () => {
                const addressId = inputAddressId ? inputAddressId.value : "";
                const name = inputName ? inputName.value.trim() : "";
                const phone = inputPhone ? inputPhone.value.trim() : "";
                const street = inputStreet ? inputStreet.value.trim() : "";
                const city = inputCity ? inputCity.value.trim() : "";
                const email = inputEmail ? inputEmail.value.trim() : "";
                const isDefault = inputIsDefault ? inputIsDefault.checked : false;

                if (!name || !phone || !street) {
                    alert("Vui lòng điền đầy đủ Họ tên, Số điện thoại và Địa chỉ nhận hàng cụ thể.");
                    return;
                }
                saveInlineAddrBtn.disabled = true;
                saveInlineAddrBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Đang lưu...`;

                try {
                    const res = await rpc("/shop/beautymatch/save_address", {
                        address_id: addressId ? parseInt(addressId, 10) : null,
                        name: name,
                        phone: phone,
                        street: street,
                        city: city || "Hà Nội",
                        email: email || "",
                        is_default: isDefault,
                    });
                    if (res && res.success) {
                        window.location.reload();
                    } else {
                        alert((res && res.error) || "Không thể lưu địa chỉ.");
                        saveInlineAddrBtn.disabled = false;
                        saveInlineAddrBtn.innerHTML = `<i class="fa fa-save me-1"></i>Hoàn thành`;
                    }
                } catch (err) {
                    console.error("Lỗi lưu địa chỉ:", err);
                    alert("Đã xảy ra lỗi khi lưu địa chỉ. Vui lòng thử lại.");
                    saveInlineAddrBtn.disabled = false;
                    saveInlineAddrBtn.innerHTML = `<i class="fa fa-save me-1"></i>Hoàn thành`;
                }
            });
        }
    }

    initDelivery() {
        const deliveryRadios = this.el.querySelectorAll(".bm-delivery-radio");
        deliveryRadios.forEach((radio) => {
            radio.addEventListener("change", async (e) => {
                const dmId = e.target.value;
                try {
                    await rpc("/shop/set_delivery_method", { dm_id: dmId });
                    window.location.reload();
                } catch (err) {
                    console.error("Lỗi chọn phương thức giao hàng:", err);
                }
            });
        });
    }
}

registry.category("public.interactions").add("beautymatch.checkout_interaction", BeautyMatchCheckout);
