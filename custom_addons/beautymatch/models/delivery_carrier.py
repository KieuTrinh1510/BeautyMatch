# -*- coding: utf-8 -*-
from odoo import api, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def _get_conversion_currencies(self, order, conversion):
        """BeautyMatch VND currency support:
        Ensure carrier rate conversion uses carrier currency (VND)
        instead of defaulting to the base company currency (USD).
        """
        carrier_currency = (
            self.currency_id
            or (self.company_id or order.company_id or self.env['res.company']._get_main_company()).currency_id
        )
        pricelist_currency = order.currency_id

        if conversion == 'company_to_pricelist':
            return carrier_currency, pricelist_currency
        elif conversion == 'pricelist_to_company':
            return pricelist_currency, carrier_currency

    @api.model
    def _archive_demo_carriers(self):
        """Archive demo carriers to ensure only BeautyMatch carrier is available."""
        demo_xml_ids = [
            'delivery.free_delivery_carrier',
            'delivery.delivery_carrier',
            'delivery.delivery_local_delivery',
        ]
        for xml_id in demo_xml_ids:
            carrier = self.env.ref(xml_id, raise_if_not_found=False)
            if carrier and carrier.active:
                carrier.write({'active': False, 'is_published': False})

        # Ensure any other non-beautymatch carriers are not published on website
        bm_carrier = self.env.ref('beautymatch.beautymatch_delivery_carrier_standard', raise_if_not_found=False)
        if bm_carrier:
            other_published = self.search([
                ('id', '!=', bm_carrier.id),
                ('website_published', '=', True),
            ])
            if other_published:
                other_published.write({'website_published': False})
