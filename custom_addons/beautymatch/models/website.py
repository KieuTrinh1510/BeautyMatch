# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    @api.depends('company_id')
    def _compute_currency_id(self):
        for website in self:
            if request and hasattr(request, 'pricelist') and request.pricelist:
                website.currency_id = request.pricelist.currency_id
            elif website.pricelist_ids:
                website.currency_id = website.pricelist_ids[0].currency_id
            else:
                vnd = self.env['res.currency'].search([('name', '=', 'VND')], limit=1)
                website.currency_id = vnd or website.company_id.sudo().currency_id
