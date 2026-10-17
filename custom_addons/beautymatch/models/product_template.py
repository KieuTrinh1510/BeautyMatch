# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    beautymatch_brand = fields.Char(
        string='Thương hiệu',
        help='Thương hiệu sản phẩm (ví dụ: CeraVe, La Roche-Posay, The Ordinary).',
    )

    beautymatch_skin_type = fields.Selection(
        selection=[
            ('oily', 'Da dầu'),
            ('dry', 'Da khô'),
            ('combination', 'Da hỗn hợp'),
            ('normal', 'Da thường'),
            ('sensitive', 'Da nhạy cảm'),
            ('all', 'Mọi loại da'),
        ],
        string='Loại da phù hợp',
        help='Loại da phù hợp nhất với sản phẩm này.',
    )

    beautymatch_skin_concern = fields.Selection(
        selection=[
            ('acne_oil', 'Dầu & mụn'),
            ('dryness', 'Khô da'),
            ('sensitivity', 'Nhạy cảm'),
            ('dullness', 'Xỉn màu'),
            ('pores', 'Lỗ chân lông'),
            ('barrier', 'Hàng rào bảo vệ da'),
        ],
        string='Vấn đề da chính',
        help='Vấn đề da chính mà sản phẩm hỗ trợ cải thiện.',
    )

    beautymatch_key_ingredients = fields.Char(
        string='Thành phần nổi bật',
        help='Các hoạt chất hoặc thành phần chính (ví dụ: Niacinamide 10%, Hyaluronic Acid, Ceramide).',
    )

    beautymatch_routine_step = fields.Selection(
        selection=[
            ('cleanser', 'Làm sạch'),
            ('toner', 'Cân bằng'),
            ('serum', 'Serum'),
            ('moisturizer', 'Dưỡng ẩm'),
            ('sunscreen', 'Chống nắng'),
            ('treatment', 'Treatment'),
        ],
        string='Bước trong routine',
        help='Vị trí của sản phẩm trong quy trình chăm sóc da hàng ngày.',
    )

    beautymatch_usage_time = fields.Selection(
        selection=[
            ('am', 'Buổi sáng'),
            ('pm', 'Buổi tối'),
            ('both', 'Sáng & tối'),
        ],
        string='Thời điểm sử dụng',
        help='Thời điểm khuyên dùng trong ngày.',
    )

    beautymatch_origin = fields.Char(
        string='Xuất xứ',
        help='Quốc gia hoặc vùng sản xuất (ví dụ: Hàn Quốc, Nhật Bản, Pháp, Việt Nam).',
    )

    beautymatch_volume = fields.Char(
        string='Dung tích',
        help='Dung tích hoặc khối lượng sản phẩm (ví dụ: 50ml, 150ml, 30g).',
    )

    beautymatch_short_fit_reason = fields.Text(
        string='Vì sao phù hợp?',
        help='Giải thích ngắn gọn lý do sản phẩm phù hợp cho khách hàng, hỗ trợ ra quyết định.',
    )

    beautymatch_budget_level = fields.Selection(
        selection=[
            ('budget', 'Tiết kiệm'),
            ('mid', 'Tầm trung'),
            ('premium', 'Cao cấp'),
        ],
        string='Phân khúc ngân sách',
        help='Phân khúc giá để đề xuất sản phẩm theo ngân sách.',
    )

    beautymatch_is_featured = fields.Boolean(
        string='Sản phẩm nổi bật',
        default=False,
        help='Đánh dấu sản phẩm nổi bật trên các trang khám phá BeautyMatch.',
    )

    beautymatch_is_quiz_recommended = fields.Boolean(
        string='Đề xuất trong Beauty Quiz',
        default=False,
        help='Ưu tiên đề xuất sản phẩm này khi khách hàng hoàn thành bài Beauty Quiz.',
    )

    @api.model
    def _setup_beautymatch_demo_inventory(self):
        """Thiết lập SKU, giá biến thể và tồn kho ban đầu (demo) cho 15 sản phẩm BeautyMatch"""
        # 1. Cấu hình biến thể CeraVe Cleanser (236ml và 473ml)
        cerave_tmpl = self.env.ref('beautymatch.product_template_cerave_cleanser', raise_if_not_found=False)
        val_236 = self.env.ref('beautymatch.product_attribute_value_volume_236ml', raise_if_not_found=False)
        val_473 = self.env.ref('beautymatch.product_attribute_value_volume_473ml', raise_if_not_found=False)

        if cerave_tmpl and val_236 and val_473:
            ptav_473 = self.env['product.template.attribute.value'].search([
                ('product_tmpl_id', '=', cerave_tmpl.id),
                ('product_attribute_value_id', '=', val_473.id),
            ], limit=1)
            if ptav_473:
                ptav_473.price_extra = 120000.0  # 370k + 120k = 490k

            # Cập nhật mã SKU riêng cho 2 biến thể
            for variant in cerave_tmpl.product_variant_ids:
                val_ids = variant.product_template_variant_value_ids.product_attribute_value_id.ids
                if val_236.id in val_ids:
                    variant.default_code = 'CV-FFC-236'
                elif val_473.id in val_ids:
                    variant.default_code = 'CV-FFC-473'

        # 2. Cài đặt tồn kho demo (45 sản phẩm cho mỗi item / biến thể)
        warehouse = self.env.ref('stock.warehouse0', raise_if_not_found=False)
        location = warehouse.lot_stock_id if warehouse else self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
        if not location:
            return

        demo_xml_ids = [
            'product_template_cerave_cleanser',
            'product_template_lrp_effaclar',
            'product_template_cetaphil_cleanser',
            'product_template_hadalabo_lotion',
            'product_template_klairs_toner',
            'product_template_somebymi_toner',
            'product_template_to_niacinamide',
            'product_template_vichy_mineral89',
            'product_template_melanocc_essence',
            'product_template_cerave_cream',
            'product_template_lrp_cicaplast',
            'product_template_neutrogena_gel',
            'product_template_anessa_sunscreen',
            'product_template_lrp_anthelios',
            'product_template_skinaqua_sunscreen',
        ]

        Quant = self.env['stock.quant']
        for xml_id in demo_xml_ids:
            tmpl = self.env.ref(f'beautymatch.{xml_id}', raise_if_not_found=False)
            if not tmpl:
                continue
            for variant in tmpl.product_variant_ids:
                quant = Quant.search([
                    ('product_id', '=', variant.id),
                    ('location_id', '=', location.id),
                ], limit=1)
                if not quant:
                    quant = Quant.create({
                        'product_id': variant.id,
                        'location_id': location.id,
                        'inventory_quantity': 45.0,
                    })
                else:
                    quant.inventory_quantity = 45.0
                quant.action_apply_inventory()

        # Tự động nạp review mẫu cho sản phẩm
        self._seed_beautymatch_demo_reviews()

    @api.model
    def _seed_beautymatch_demo_reviews(self):
        """Tạo sẵn các đánh giá y khoa / trải nghiệm thực tế cho sản phẩm BeautyMatch"""
        Rating = self.env['rating.rating'].sudo()
        Message = self.env['mail.message'].sudo()
        model_id = self.env['ir.model']._get_id('product.template')
        partner = self.env.ref('base.partner_admin', raise_if_not_found=False)
        if not partner or not model_id:
            return

        reviews_data = [
            (
                'product_template_cerave_cleanser',
                5.0,
                'Sữa rửa mặt chân ái cho da dầu mụn. Rửa xong da thông thoáng, kiềm dầu rất tốt mà vẫn giữ được độ ẩm tự nhiên, không hề bị rát hay căng kích nhờ có Ceramide.',
            ),
            (
                'product_template_lrp_effaclar',
                5.0,
                'Bọt xốp mịn, giảm sợi bã nhờn ở vùng mũi cực rõ chỉ sau 1 tuần dùng. Rất khuyến khích cho các bạn có làn da dầu mụn nhạy cảm.',
            ),
            (
                'product_template_klairs_toner',
                5.0,
                'Toner không mùi, cấp ẩm tầng sâu cực đỉnh. Dùng phương pháp vỗ 3 lớp toner buổi tối da mọng nước và dịu mẩn đỏ tức thì.',
            ),
            (
                'product_template_to_niacinamide',
                5.0,
                'Serum Niacinamide 10% kết hợp Kẽm 1% kiềm dầu thần sầu và hỗ trợ mờ thâm mụn mới rất nhanh.',
            ),
            (
                'product_template_anessa_sunscreen',
                5.0,
                'Kem chống nắng quốc dân, chống nước đỉnh cao, ráo mặt cả ngày không xuống tone và không gây bít tắc chân lông.',
            ),
            (
                'product_template_lrp_cicaplast',
                5.0,
                'Kem dưỡng phục hồi B5+ đỉnh nhất từng dùng. Da treatment hay bong tróc bôi qua đêm là sáng hôm sau êm ru.',
            ),
        ]

        for xml_id, rating_val, feedback in reviews_data:
            tmpl = self.env.ref(f'beautymatch.{xml_id}', raise_if_not_found=False)
            if not tmpl:
                continue
            existing = Rating.search([
                ('res_model_id', '=', model_id),
                ('res_id', '=', tmpl.id),
            ], limit=1)
            if not existing:
                msg = Message.create({
                    'model': 'product.template',
                    'res_id': tmpl.id,
                    'body': f'<p>{feedback}</p>',
                    'message_type': 'comment',
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                    'author_id': partner.id,
                })
                Rating.create({
                    'res_model_id': model_id,
                    'res_id': tmpl.id,
                    'rating': rating_val,
                    'consumed': True,
                    'is_internal': False,
                    'partner_id': partner.id,
                    'feedback': feedback,
                    'message_id': msg.id,
                })
                tmpl._compute_rating_stats()

    @api.model
    def _get_website_sale_search_fields(self, search_in_description=True):
        """Mở rộng tìm kiếm sản phẩm theo thương hiệu, thành phần nổi bật và danh mục"""
        search_fields = super()._get_website_sale_search_fields(search_in_description=search_in_description)
        search_fields = list(search_fields)
        for custom_field in ['beautymatch_brand', 'beautymatch_key_ingredients', 'public_categ_ids.name']:
            if custom_field not in search_fields:
                search_fields.append(custom_field)
        return search_fields

    @api.model
    def _search_get_detail(self, website, order, options):
        """Tích hợp các tiêu chí lọc da liễu vào domain tìm kiếm eCommerce"""
        from odoo.fields import Domain
        res = super()._search_get_detail(website, order, options)
        domains = res.get('base_domain', [])
        extra_domains = []

        skin_types = options.get('skin_type')
        if skin_types:
            skin_conds = [Domain('beautymatch_skin_type', '=', st) for st in skin_types if st]
            if skin_conds:
                skin_conds.append(Domain('beautymatch_skin_type', '=', 'all'))
                extra_domains.append(Domain.OR(skin_conds))

        concerns = options.get('concern')
        if concerns:
            concerns = [c for c in concerns if c]
            if concerns:
                extra_domains.append(Domain('beautymatch_skin_concern', 'in', concerns))

        brands = options.get('brand')
        if brands:
            brands = [b for b in brands if b]
            if brands:
                extra_domains.append(Domain('beautymatch_brand', 'in', brands))

        ingredients = options.get('ingredient')
        if ingredients:
            ingr_conds = [Domain('beautymatch_key_ingredients', 'ilike', ingr) for ingr in ingredients if ingr]
            if ingr_conds:
                extra_domains.append(Domain.OR(ingr_conds))

        budgets = options.get('budget')
        if budgets:
            budgets = [bg for bg in budgets if bg]
            if budgets:
                extra_domains.append(Domain('beautymatch_budget_level', 'in', budgets))

        volumes = options.get('volume')
        if volumes:
            vol_conds = [Domain('beautymatch_volume', 'ilike', vol) for vol in volumes if vol]
            if vol_conds:
                extra_domains.append(Domain.OR(vol_conds))

        if extra_domains:
            domains.append(Domain.AND(extra_domains))
            res['base_domain'] = domains

        return res

    @api.depends('company_id')
    def _compute_currency_id(self):
        super()._compute_currency_id()
        vnd = self.env['res.currency'].search([('name', '=', 'VND')], limit=1)
        if vnd:
            for template in self:
                if template.beautymatch_brand or template.type == 'service':
                    template.currency_id = vnd.id

