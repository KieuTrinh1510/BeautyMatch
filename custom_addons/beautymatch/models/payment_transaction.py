# -*- coding: utf-8 -*-
from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _compute_sale_order_reference(self, order):
        """Prefix sale order payment reference with BM for BeautyMatch communication."""
        ref = super()._compute_sale_order_reference(order)
        if ref:
            return ref if ref.startswith('BM ') else f"BM {ref}"
        return f"BM {order.name}"

    def _post_process(self):
        """Chặn tự động xác nhận đơn bán hàng khi khách đặt đơn trên website.
        Quy trình chuẩn BeautyMatch:
        - Khách đặt COD / Chuyển khoản -> Đơn giữ ở trạng thái 'sent' (Chờ xác nhận).
        - Admin mở backend Odoo (Sales -> Orders) -> Kiểm tra đơn -> Bấm [Xác nhận].
        - Sau khi Admin xác nhận thì đơn mới chuyển sang 'sale' và sinh Delivery Order.
        """
        # Đảm bảo các đơn hàng liên kết ở trạng thái 'sent' và có mã tham chiếu BM chuẩn
        for tx in self:
            for order in tx.sale_order_ids:
                if order.state == 'draft':
                    order.write({'state': 'sent'})
                if not order.reference and order.name:
                    order.reference = f"BM {order.name}"

        # Truyền context prevent_auto_confirm=True để chặn delivery và sale auto-confirm
        return super(
            PaymentTransaction,
            self.with_context(prevent_auto_confirm=True)
        )._post_process()

    def _check_amount_and_confirm_order(self):
        """Chặn tự động xác nhận từ module payment/sale khi giao dịch hoàn tất."""
        # BeautyMatch yêu cầu admin duyệt thủ công trong backend
        return self.env['sale.order']
