# -*- coding: utf-8 -*-
from odoo import api, fields, models
# pyrefly: ignore[missing-import]
from odoo.exceptions import UserError
from odoo.http import request


import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if not order.reference and order.name:
                order.reference = f"BM {order.name}"
        return orders

    def action_confirm(self):
        # 1. Chặn xác nhận tự động khi giao dịch được tạo từ luồng checkout website
        if self.env.context.get('prevent_auto_confirm'):
            for order in self:
                if order.state == 'draft':
                    order.write({'state': 'sent'})
                if not order.reference and order.name:
                    order.reference = f"BM {order.name}"
            return False

        # 2. Xác nhận thủ công từ Admin Backend Odoo (Sales -> Orders -> Bấm [Xác nhận])
        for order in self:
            if not order.reference and order.name:
                order.reference = f"BM {order.name}"
        return super().action_confirm()

    # Tracking compute fields
    bm_tracking_step = fields.Integer(
        string="Bước tiến trình",
        compute="_compute_beautymatch_tracking",
        store=False,
    )
    bm_tracking_label = fields.Char(
        string="Trạng thái theo dõi",
        compute="_compute_beautymatch_tracking",
        store=False,
    )
    bm_tracking_badge_class = fields.Char(
        string="Class badge",
        compute="_compute_beautymatch_tracking",
        store=False,
    )

    @api.depends('state', 'picking_ids', 'picking_ids.state', 'delivery_status', 'invoice_status', 'amount_paid')
    def _compute_beautymatch_tracking(self):
        for order in self:
            info = order._get_beautymatch_tracking_status()
            order.bm_tracking_step = info['step']
            order.bm_tracking_label = info['label']
            order.bm_tracking_badge_class = info['badge_class']

    def _get_beautymatch_tracking_status(self):
        self.ensure_one()
        if self.state == 'cancel':
            return {
                'step': -1,
                'status': 'cancelled',
                'label': 'Đã hủy',
                'badge_class': 'badge rounded-pill text-bg-danger',
                'steps': [
                    {'num': 1, 'name': 'Đặt hàng', 'icon': 'fa-shopping-cart', 'status': 'completed'},
                    {'num': 2, 'name': 'Đã hủy', 'icon': 'fa-times-circle', 'status': 'cancelled'},
                ],
            }

        # Step 1: Chờ xác nhận
        # Step 2: Đã xác nhận
        # Step 3: Đang chuẩn bị
        # Step 4: Đang giao
        # Step 5: Đã giao
        pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_id.code == 'outgoing' and p.state != 'cancel'
        )

        if self.state in ('draft', 'sent'):
            current_step = 1
            label = 'Chờ xác nhận'
            badge_class = 'badge rounded-pill text-bg-warning text-dark'
        elif not pickings:
            current_step = 2
            label = 'Đã xác nhận'
            badge_class = 'badge rounded-pill text-bg-info text-white'
        else:
            if all(p.state == 'done' for p in pickings):
                if self.invoice_status == 'invoiced' or (self.amount_paid and self.amount_paid >= self.amount_total):
                    current_step = 5
                    label = 'Đã giao'
                    badge_class = 'badge rounded-pill text-bg-success'
                else:
                    current_step = 4
                    label = 'Đang giao'
                    badge_class = 'badge rounded-pill text-bg-primary'
            elif any(p.state in ('assigned', 'confirmed') for p in pickings):
                current_step = 3
                label = 'Đang chuẩn bị'
                badge_class = 'badge rounded-pill text-bg-info text-white'
            else:
                current_step = 2
                label = 'Đã xác nhận'
                badge_class = 'badge rounded-pill text-bg-info text-white'

        steps = [
            {
                'num': 1,
                'name': 'Đặt hàng',
                'icon': 'fa-shopping-bag',
                'status': 'completed' if current_step > 1 else ('active' if current_step == 1 else 'pending'),
            },
            {
                'num': 2,
                'name': 'Đã xác nhận',
                'icon': 'fa-check-circle',
                'status': 'completed' if current_step > 2 else ('active' if current_step == 2 else 'pending'),
            },
            {
                'num': 3,
                'name': 'Đang chuẩn bị',
                'icon': 'fa-box',
                'status': 'completed' if current_step > 3 else ('active' if current_step == 3 else 'pending'),
            },
            {
                'num': 4,
                'name': 'Đang giao',
                'icon': 'fa-truck',
                'status': 'completed' if current_step > 4 else ('active' if current_step == 4 else 'pending'),
            },
            {
                'num': 5,
                'name': 'Đã giao',
                'icon': 'fa-home',
                'status': 'completed' if current_step == 5 else 'pending',
            },
        ]

        return {
            'step': current_step,
            'label': label,
            'badge_class': badge_class,
            'steps': steps,
        }

    def _get_beautymatch_payment_info(self):
        self.ensure_one()
        tx = self.get_portal_last_transaction()
        provider_name = tx.provider_id.name if tx else ''
        custom_mode = tx.provider_id.custom_mode if tx and tx.provider_id else ''

        is_cod = 'cash_on_delivery' in (custom_mode or '') or 'nhận hàng' in (provider_name or '').lower() or 'cod' in (provider_name or '').lower()
        is_wire = 'wire_transfer' in (custom_mode or '') or 'chuyển khoản' in (provider_name or '').lower() or 'wire' in (provider_name or '').lower()

        if is_cod:
            method_name = 'Thanh toán khi nhận hàng (COD)'
            status_label = 'Chờ thanh toán khi nhận hàng'
            status_badge = 'badge rounded-pill text-bg-warning text-dark'
        elif is_wire:
            method_name = 'Chuyển khoản ngân hàng'
            if tx and tx.state == 'done':
                status_label = 'Đã thanh toán'
                status_badge = 'badge rounded-pill text-bg-success'
            else:
                status_label = 'Chờ chuyển khoản'
                status_badge = 'badge rounded-pill text-bg-info text-white'
        elif tx:
            method_name = provider_name
            status_label = 'Đã thanh toán' if tx.state == 'done' else 'Đang xử lý'
            status_badge = 'badge rounded-pill text-bg-success' if tx.state == 'done' else 'badge rounded-pill text-bg-info'
        else:
            method_name = 'Chưa xác định'
            status_label = 'Chờ thanh toán'
            status_badge = 'badge rounded-pill text-bg-secondary'

        transfer_ref = f"BM {self.name}"

        return {
            'method_name': method_name,
            'status_label': status_label,
            'status_badge': status_badge,
            'is_cod': is_cod,
            'is_wire': is_wire,
            'bank_name': 'BeautyMatch Demo Bank',
            'account_holder': 'BEAUTYMATCH',
            'account_number': '0000000000',
            'transfer_ref': transfer_ref,
        }

    def _get_beautymatch_shipping_info(self):
        self.ensure_one()
        carrier_name = self.carrier_id.name if self.carrier_id else 'Giao hàng tiêu chuẩn'
        delivery_line = self.order_line.filtered(lambda l: l.is_delivery)
        price = delivery_line.price_unit if delivery_line else self.amount_delivery

        is_free = (price == 0.0)

        return {
            'carrier_name': carrier_name,
            'price': price,
            'is_free': is_free,
            'price_formatted': 'Miễn phí' if is_free else f"{price:,.0f} ₫",
        }

    def _send_order_confirmation_mail(self):
        """Safely handle order confirmation email sending in environments
        without wkhtmltopdf or SMTP configured (non-blocking).
        """
        try:
            return super()._send_order_confirmation_mail()
        except Exception as e:
            _logger.warning("Could not send order confirmation email (non-blocking): %s", e)
            return False

    def _send_payment_succeeded_for_order_mail(self):
        """Safely handle payment notification email sending in environments
        without wkhtmltopdf or SMTP configured (non-blocking).
        """
        try:
            return super()._send_payment_succeeded_for_order_mail()
        except Exception as e:
            _logger.warning("Could not send payment notification email (non-blocking): %s", e)
            return False

    def _try_pending_coupon(self):
        if not request:
            return False
        pending_coupon_code = request.session.pop('pending_coupon_code', None)
        if pending_coupon_code:
            try:
                status = self._try_apply_code(pending_coupon_code)
                if isinstance(status, dict) and 'error' not in status:
                    if len(status) == 1:
                        coupon, rewards = next(iter(status.items()))
                        if len(rewards) == 1 and not getattr(rewards, 'multi_product', False):
                            self._apply_program_reward(rewards, coupon)
                return status
            except Exception as e:
                _logger.warning("Could not apply pending coupon %s: %s", pending_coupon_code, e)
                return {'error': str(e)}
        return True

    def _try_apply_code(self, code):
        clean_code = (code or '').strip().upper()
        if clean_code == 'BEAUTY50':
            order_amount = sum(
                line.price_total for line in self.order_line.filtered(
                    lambda l: not l.is_delivery and not l.is_reward_line and not l.reward_id
                )
            )
            if order_amount < 700000:
                return {'error': "Đơn hàng chưa đạt giá trị tối thiểu 700.000đ để sử dụng mã BEAUTY50."}
        return super()._try_apply_code(code)

    def _get_beautymatch_voucher_summary(self):
        self.ensure_one()
        # 1. Base subtotal of items without delivery and reward lines
        item_lines = self.order_line.filtered(
            lambda l: not l.is_delivery and not l.is_reward_line and not l.reward_id
        )
        subtotal_items = sum(line.price_total for line in item_lines)

        # 2. Check currently applied voucher
        applied_code = False
        reward_amount = 0.0
        reward_lines = self.order_line.filtered(lambda l: l.is_reward_line or l.reward_id)
        if reward_lines:
            reward_amount = abs(sum(line.price_total for line in reward_lines))
            rule_codes = self.code_enabled_rule_ids.mapped('code')
            if 'WELCOME10' in rule_codes:
                applied_code = 'WELCOME10'
            elif 'BEAUTY50' in rule_codes:
                applied_code = 'BEAUTY50'
            else:
                for line in reward_lines:
                    name_upper = (line.name or '').upper()
                    if 'WELCOME10' in name_upper:
                        applied_code = 'WELCOME10'
                        break
                    elif 'BEAUTY50' in name_upper:
                        applied_code = 'BEAUTY50'
                        break

        # 3. Check customer previous orders for WELCOME10 eligibility
        is_first_order = True
        is_public = self.env.user._is_public() if hasattr(self.env.user, '_is_public') else self.env.user.has_group('base.group_public')
        if self.partner_id and not is_public:
            prev_orders = self.env['sale.order'].sudo().search_count([
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('state', 'in', ['sale', 'done']),
                ('id', '!=', self.id),
            ])
            if prev_orders > 0:
                is_first_order = False

        welcome10_eligible = is_first_order
        welcome10_reason = "Áp dụng cho đơn hàng đầu tiên" if is_first_order else "Chỉ dành cho đơn đầu tiên"

        # 4. Check BEAUTY50 eligibility (requires subtotal >= 700.000đ)
        beauty50_eligible = (subtotal_items >= 700000)
        missing_for_beauty50 = max(0, 700000 - subtotal_items)
        if beauty50_eligible:
            beauty50_reason = "Đơn hàng đủ điều kiện từ 700.000đ"
        else:
            beauty50_reason = f"Mua thêm {missing_for_beauty50:,.0f}đ để dùng mã này"

        return {
            'applied_code': applied_code,
            'reward_amount': reward_amount,
            'subtotal_items': subtotal_items,
            'vouchers': [
                {
                    'code': 'WELCOME10',
                    'title': 'WELCOME10',
                    'discount_badge': 'GIẢM 10%',
                    'description': 'Giảm ngay 10% trên tổng giá trị sản phẩm đơn hàng đầu tiên.',
                    'is_eligible': welcome10_eligible,
                    'is_applied': (applied_code == 'WELCOME10'),
                    'reason': welcome10_reason,
                    'missing_amount': 0,
                },
                {
                    'code': 'BEAUTY50',
                    'title': 'BEAUTY50',
                    'discount_badge': 'GIẢM 50.000đ',
                    'description': 'Giảm trực tiếp 50.000đ cho đơn hàng có giá trị từ 700.000đ.',
                    'is_eligible': beauty50_eligible,
                    'is_applied': (applied_code == 'BEAUTY50'),
                    'reason': beauty50_reason,
                    'missing_amount': missing_for_beauty50,
                },
            ],
        }

    def _apply_beautymatch_single_voucher(self, code):
        self.ensure_one()
        clean_code = (code or '').strip().upper()
        _logger.info("Applying BeautyMatch voucher: %s to Order %s", clean_code, self.name)

        # 1. Luôn gỡ bỏ triệt để voucher/reward cũ trước khi áp dụng mã mới
        reward_lines = self.order_line.filtered(lambda l: l.is_reward_line or l.reward_id)
        if reward_lines:
            reward_lines.unlink()
        self.applied_coupon_ids = False
        promo_rules = self.env['loyalty.rule'].sudo().search([('code', 'in', ['WELCOME10', 'BEAUTY50'])])
        self.code_enabled_rule_ids -= promo_rules
        self._update_programs_and_rewards()

        # 2. Nếu mã rỗng hoặc 'NONE' -> khách muốn bỏ voucher
        if not clean_code or clean_code == 'NONE':
            if self.carrier_id:
                rate = self.carrier_id.rate_shipment(self)
                if rate.get('success'):
                    self.set_delivery_line(self.carrier_id, rate['price'])
            self._update_programs_and_rewards()
            return {'success': True, 'applied_code': False}

        # 3. Kiểm tra điều kiện mã BEAUTY50
        if clean_code == 'BEAUTY50':
            subtotal = sum(
                l.price_total for l in self.order_line.filtered(
                    lambda l: not l.is_delivery and not l.is_reward_line and not l.reward_id
                )
            )
            if subtotal < 700000:
                missing = 700000 - subtotal
                return {
                    'error': f"Đơn hàng chưa đạt giá trị tối thiểu 700.000đ (còn thiếu {missing:,.0f}đ) để áp dụng mã BEAUTY50."
                }

        # 4. Áp dụng mã
        status = self._try_apply_code(clean_code)
        if status and isinstance(status, dict) and 'error' in status:
            return {'error': status['error']}

        if isinstance(status, dict) and len(status) == 1:
            coupon, rewards = next(iter(status.items()))
            if len(rewards) == 1 and not getattr(rewards, 'multi_product', False):
                self._apply_program_reward(rewards, coupon)

        self._update_programs_and_rewards()

        # 5. Cập nhật lại phí vận chuyển sau khi giảm giá
        if self.carrier_id:
            rate = self.carrier_id.rate_shipment(self)
            if rate.get('success'):
                self.set_delivery_line(self.carrier_id, rate['price'])
        self._update_programs_and_rewards()

        return {'success': True, 'applied_code': clean_code}

    # Cart Selection & Splitting (Shopee Style)
    bm_is_retained_cart = fields.Boolean(
        string="Giỏ hàng lưu giữ",
        default=False,
    )
    bm_selected_subtotal = fields.Monetary(
        string="Tạm tính sản phẩm chọn",
        compute="_compute_bm_cart_selection",
        store=False,
    )
    bm_selected_tax = fields.Monetary(
        string="Thuế sản phẩm chọn",
        compute="_compute_bm_cart_selection",
        store=False,
    )
    bm_selected_total = fields.Monetary(
        string="Tổng tiền sản phẩm chọn",
        compute="_compute_bm_cart_selection",
        store=False,
    )
    bm_selected_count = fields.Integer(
        string="Số lượng sản phẩm chọn",
        compute="_compute_bm_cart_selection",
        store=False,
    )
    bm_total_selectable_count = fields.Integer(
        string="Tổng số sản phẩm",
        compute="_compute_bm_cart_selection",
        store=False,
    )
    bm_all_selected = fields.Boolean(
        string="Đã chọn tất cả",
        compute="_compute_bm_cart_selection",
        store=False,
    )

    @api.depends('order_line.bm_is_selected', 'order_line.price_subtotal', 'order_line.price_total', 'order_line.price_tax', 'order_line.product_uom_qty')
    def _compute_bm_cart_selection(self):
        for order in self:
            prod_lines = order.order_line.filtered(
                lambda l: not l.is_reward_line and not l.is_delivery and not l.reward_id
            )
            selected_lines = prod_lines.filtered('bm_is_selected')
            order.bm_total_selectable_count = len(prod_lines)
            order.bm_selected_count = len(selected_lines)
            order.bm_selected_subtotal = sum(l.price_subtotal for l in selected_lines)
            order.bm_selected_tax = sum(l.price_tax for l in selected_lines)
            order.bm_selected_total = sum(l.price_total for l in selected_lines)
            order.bm_all_selected = bool(prod_lines and len(selected_lines) == len(prod_lines))

    def _clean_beautymatch_rewards(self):
        """Xóa triệt để các reward lines cũ để tránh ưu đãi ngầm"""
        for order in self:
            reward_lines = order.order_line.filtered(lambda l: l.is_reward_line or l.reward_id)
            if reward_lines:
                reward_lines.unlink()
            order.applied_coupon_ids = False
            promo_rules = self.env['loyalty.rule'].sudo().search([('code', 'in', ['WELCOME10', 'BEAUTY50'])])
            order.code_enabled_rule_ids -= promo_rules
            order._update_programs_and_rewards()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    bm_is_selected = fields.Boolean(
        string="Được chọn thanh toán",
        default=True,
    )

    def _show_in_cart(self):
        # Không bao giờ hiển thị dòng voucher / giảm giá như một sản phẩm thông thường trong giỏ hàng
        if self.is_reward_line or self.reward_id:
            return False
        return super()._show_in_cart()

    def _set_shop_warning_stock(self, desired_qty, new_qty, save=True):
        self.ensure_one()
        warning = "Sản phẩm này hiện không đủ số lượng tồn kho."
        if save:
            self.shop_warning = warning
        return warning


