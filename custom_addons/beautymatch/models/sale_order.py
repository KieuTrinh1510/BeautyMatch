# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


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
        without wkhtmltopdf installed (such as local dev macOS).
        """
        try:
            return super()._send_order_confirmation_mail()
        except UserError as e:
            if "Wkhtmltopdf" in str(e):
                pass
            else:
                raise

    def _send_payment_succeeded_for_order_mail(self):
        """Safely handle payment notification email sending in environments
        without wkhtmltopdf installed (such as local dev macOS).
        """
        try:
            return super()._send_payment_succeeded_for_order_mail()
        except UserError as e:
            if "Wkhtmltopdf" in str(e):
                pass
            else:
                raise

