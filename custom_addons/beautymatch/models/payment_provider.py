# -*- coding: utf-8 -*-
from odoo import api, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    @api.model
    def _setup_beautymatch_payment_providers(self):
        """Configure BeautyMatch Payment Providers (COD & Bank Wire Transfer)
        and disable all other external / demo providers.
        """
        # 1. Ensure Standard Carrier allows COD
        carrier = self.env.ref(
            'beautymatch.beautymatch_delivery_carrier_standard', raise_if_not_found=False
        )
        if carrier and not carrier.allow_cash_on_delivery:
            carrier.write({'allow_cash_on_delivery': True})

        # 2. Get payment methods
        m_cod = self.env.ref(
            'delivery.payment_method_cash_on_delivery', raise_if_not_found=False
        ) or self.env['payment.method'].with_context(active_test=False).search(
            [('code', '=', 'cash_on_delivery')], limit=1
        )

        m_wire = self.env.ref(
            'payment_custom.payment_method_wire_transfer', raise_if_not_found=False
        ) or self.env['payment.method'].with_context(active_test=False).search(
            [('code', '=', 'wire_transfer')], limit=1
        )

        # 3. Configure COD Provider
        p_cod = self.env.ref(
            'delivery.payment_provider_cod', raise_if_not_found=False
        ) or self.search([('custom_mode', '=', 'cash_on_delivery')], limit=1)

        if p_cod:
            cod_vals = {
                'name': 'Thanh toán khi nhận hàng (COD)',
                'state': 'enabled',
                'is_published': True,
                'pre_msg': '<p class="mb-0">Thanh toán bằng tiền mặt khi nhận sản phẩm.</p>',
                'pending_msg': '<p class="mb-0">Bạn thanh toán khi nhận hàng. Nhân viên giao hàng sẽ liên hệ thu tiền khi giao sản phẩm.</p>',
                'done_msg': '<p class="mb-0">Đơn hàng đã được thanh toán thành công.</p>',
            }
            if m_cod:
                cod_vals['payment_method_ids'] = [(6, 0, [m_cod.id])]
            p_cod.write(cod_vals)

        # 4. Configure Bank Wire Transfer Provider
        p_wire = self.env.ref(
            'payment.payment_provider_transfer', raise_if_not_found=False
        ) or self.search([('custom_mode', '=', 'wire_transfer')], limit=1)

        bank_pending_html = """<div class="alert alert-info p-3 mb-0" style="background-color: #F3ECF8; border: 1px solid #8F6FA8;">
    <h6 class="fw-bold mb-2" style="color: #6E4C7E;"><i class="fa fa-university me-2"/>Thông tin chuyển khoản ngân hàng (Demo):</h6>
    <ul class="list-unstyled mb-2" style="color: #2B2430; line-height: 1.8;">
        <li><strong>Ngân hàng:</strong> BeautyMatch Demo Bank</li>
        <li><strong>Chủ tài khoản:</strong> BEAUTYMATCH</li>
        <li><strong>Số tài khoản:</strong> 0000000000</li>
        <li><strong>Nội dung:</strong> BM + Mã đơn hàng (Ví dụ: BM S00052)</li>
    </ul>
    <small class="text-muted fst-italic">* Lưu ý: Đây là tài khoản demo phục vụ mục đích kiểm thử/học tập, vui lòng không chuyển tiền thật.</small>
</div>"""

        if p_wire:
            wire_vals = {
                'name': 'Chuyển khoản ngân hàng',
                'state': 'enabled',
                'is_published': True,
                'pre_msg': '<p class="mb-0">Chuyển khoản theo thông tin BeautyMatch sau khi xác nhận đơn hàng.</p>',
                'pending_msg': bank_pending_html,
            }
            if m_wire:
                wire_vals['payment_method_ids'] = [(6, 0, [m_wire.id])]
            p_wire.write(wire_vals)

        # 5. Activate Payment Methods with localized BeautyMatch names
        if m_cod:
            m_cod.write({
                'name': 'Thanh toán khi nhận hàng (COD)',
                'active': True,
            })
        if m_wire:
            m_wire.write({
                'name': 'Chuyển khoản ngân hàng',
                'active': True,
            })

        # 6. Disable and unpublish all other payment providers
        active_bm_ids = [p.id for p in [p_cod, p_wire] if p]
        other_providers = self.search([
            ('id', 'not in', active_bm_ids),
            ('state', '!=', 'disabled'),
        ])
        if other_providers:
            other_providers.write({'state': 'disabled', 'is_published': False})

        # Ensure no other provider is published
        other_published = self.search([
            ('id', 'not in', active_bm_ids),
            ('is_published', '=', True),
        ])
        if other_published:
            other_published.write({'is_published': False})

        # 7. Unlink PDF reports from sale mail templates to prevent wkhtmltopdf missing error in local macOS
        sale_mail_templates = self.env['mail.template'].search([
            ('model', '=', 'sale.order'),
            ('report_template_ids', '!=', False),
        ])
        if sale_mail_templates:
            sale_mail_templates.write({'report_template_ids': [(5, 0, 0)]})
