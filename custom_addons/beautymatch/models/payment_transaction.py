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
