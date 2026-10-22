# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    bm_is_default_shipping = fields.Boolean(
        string="Địa chỉ nhận hàng mặc định",
        default=False,
    )

    def bm_set_as_default_shipping(self):
        """Đặt địa chỉ này làm địa chỉ giao hàng mặc định của khách hàng"""
        for partner in self:
            commercial = partner.commercial_partner_id
            all_addrs = self.sudo().search([
                '|',
                ('id', '=', commercial.id),
                ('parent_id', '=', commercial.id),
            ])
            all_addrs.write({'bm_is_default_shipping': False})
            partner.sudo().write({'bm_is_default_shipping': True})
