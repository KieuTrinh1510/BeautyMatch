# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.fields import Domain
from odoo.addons.website.controllers.main import Website
from odoo.addons.website_sale.controllers.main import WebsiteSale


class BeautyMatchWebsite(Website):

    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def index(self, **kw):
        """Trang chủ chuyên biệt của BeautyMatch (Dedicated Homepage)"""
        ProductTemplate = request.env['product.template'].sudo()
        # Lấy tối đa 4 sản phẩm nổi bật được cấu hình beautymatch_is_featured
        featured_products = ProductTemplate.search([
            ('website_published', '=', True),
            ('sale_ok', '=', True),
            ('beautymatch_is_featured', '=', True),
        ], limit=4, order='sequence, id desc')

        return request.render('beautymatch.homepage', {
            'featured_products': featured_products,
        })


class BeautyMatchWebsiteSale(WebsiteSale):
    """Mở rộng bộ lọc Shop (/shop) phục vụ phân loại da liễu & routine"""

    def _get_shop_domain(self, search, category, attribute_value_dict, search_in_description=True):
        domain = super()._get_shop_domain(
            search=search,
            category=category,
            attribute_value_dict=attribute_value_dict,
            search_in_description=search_in_description,
        )
        req_args = request.httprequest.args
        extra_domains = []

        # 1. Lọc theo Loại da
        skin_types = req_args.getlist('skin_type')
        if skin_types:
            skin_conds = [Domain('beautymatch_skin_type', '=', st) for st in skin_types]
            skin_conds.append(Domain('beautymatch_skin_type', '=', 'all'))
            extra_domains.append(Domain.OR(skin_conds))

        # 2. Lọc theo Vấn đề da
        concerns = req_args.getlist('concern')
        if concerns:
            extra_domains.append(Domain('beautymatch_skin_concern', 'in', concerns))

        # 3. Lọc theo Thương hiệu
        brands = req_args.getlist('brand')
        if brands:
            extra_domains.append(Domain('beautymatch_brand', 'in', brands))

        # 4. Lọc theo Hoạt chất / Thành phần
        ingredients = req_args.getlist('ingredient')
        if ingredients:
            ingr_conds = [Domain('beautymatch_key_ingredients', 'ilike', ingr) for ingr in ingredients]
            extra_domains.append(Domain.OR(ingr_conds))

        # 5. Lọc theo Phân khúc giá
        budgets = req_args.getlist('budget')
        if budgets:
            extra_domains.append(Domain('beautymatch_budget_level', 'in', budgets))

        # 6. Lọc theo Dung tích
        volumes = req_args.getlist('volume')
        if volumes:
            vol_conds = [Domain('beautymatch_volume', 'ilike', vol) for vol in volumes]
            extra_domains.append(Domain.OR(vol_conds))

        if extra_domains:
            domain = Domain.AND([domain] + extra_domains)

        return domain

    def _shop_get_query_url_kwargs(self, search, min_price, max_price, **post):
        kwargs = super()._shop_get_query_url_kwargs(search, min_price, max_price, **post)
        req_args = request.httprequest.args
        for param in ['skin_type', 'concern', 'brand', 'ingredient', 'budget', 'volume']:
            val = req_args.getlist(param)
            if val:
                kwargs[param] = val if len(val) > 1 else val[0]
        return kwargs

    def _get_search_options(self, **post):
        options = super()._get_search_options(**post)
        req_args = request.httprequest.args
        for param in ['skin_type', 'concern', 'brand', 'ingredient', 'budget', 'volume']:
            val = req_args.getlist(param)
            if val:
                options[param] = val
        return options

    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, tags='', **post):
        response = super().shop(
            page=page,
            category=category,
            search=search,
            min_price=min_price,
            max_price=max_price,
            tags=tags,
            **post,
        )
        if hasattr(response, 'qcontext'):
            req_args = request.httprequest.args
            ProductTemplate = request.env['product.template'].sudo()
            PublicCategory = request.env['product.public.category'].sudo()

            # Danh mục chính thức (Category dùng để điều hướng)
            main_categories = PublicCategory.search([], order='sequence, id')

            # Danh sách filter đã chọn
            selected_skin_types = req_args.getlist('skin_type')
            selected_concerns = req_args.getlist('concern')
            selected_brands = req_args.getlist('brand')
            selected_ingredients = req_args.getlist('ingredient')
            selected_budgets = req_args.getlist('budget')
            selected_volumes = req_args.getlist('volume')

            # Dữ liệu thuộc tính lọc da liễu
            skin_types_data = [
                ('oily', 'Da dầu'),
                ('dry', 'Da khô'),
                ('combination', 'Da hỗn hợp'),
                ('normal', 'Da thường'),
                ('sensitive', 'Da nhạy cảm'),
                ('all', 'Mọi loại da'),
            ]

            skin_concerns_data = [
                ('acne_oil', 'Dầu & mụn'),
                ('dryness', 'Khô da'),
                ('sensitivity', 'Nhạy cảm'),
                ('dullness', 'Xỉn màu'),
                ('pores', 'Lỗ chân lông'),
                ('barrier', 'Hàng rào bảo vệ'),
            ]

            budget_levels_data = [
                ('budget', 'Tiết kiệm (< 250k)'),
                ('mid', 'Tầm trung (250k - 500k)'),
                ('premium', 'Cao cấp (> 500k)'),
            ]

            # Lấy động thương hiệu từ các sản phẩm đã xuất bản
            published_products = ProductTemplate.search([
                ('website_published', '=', True),
                ('sale_ok', '=', True),
            ])
            available_brands = sorted(list({
                p.beautymatch_brand.strip() for p in published_products if p.beautymatch_brand
            }))

            # Thành phần nổi bật phổ biến
            popular_ingredients = [
                'Ceramide',
                'Niacinamide',
                'Hyaluronic Acid',
                'B5 (Panthenol)',
                'BHA',
                'AHA',
                'Zinc PCA',
                'Vitamin C',
                'Rau má',
            ]

            # Dung tích thực tế của sản phẩm
            available_volumes = sorted(list({
                p.beautymatch_volume.strip() for p in published_products if p.beautymatch_volume
            }))

            has_active_bm_filters = bool(
                selected_skin_types or selected_concerns or selected_brands
                or selected_ingredients or selected_budgets or selected_volumes
            )

            response.qcontext.update({
                'bm_main_categories': main_categories,
                'bm_skin_types_data': skin_types_data,
                'bm_skin_concerns_data': skin_concerns_data,
                'bm_budget_levels_data': budget_levels_data,
                'bm_available_brands': available_brands,
                'bm_popular_ingredients': popular_ingredients,
                'bm_available_volumes': available_volumes,
                'bm_selected_skin_types': selected_skin_types,
                'bm_selected_concerns': selected_concerns,
                'bm_selected_brands': selected_brands,
                'bm_selected_ingredients': selected_ingredients,
                'bm_selected_budgets': selected_budgets,
                'bm_selected_volumes': selected_volumes,
                'bm_has_active_filters': has_active_bm_filters,
            })

        return response


class BeautyMatchController(http.Controller):

    @http.route('/theo-van-de-da', type='http', auth='public', website=True)
    def theo_van_de_da(self, **kwargs):
        """Trang mua sắm theo vấn đề da (Shop by Skin Concern)"""
        concerns = [
            {
                'id': 'acne_oil',
                'title': 'Da dầu & mụn',
                'badge': 'Kiểm soát bã nhờn',
                'description': 'Kiểm soát dầu, làm sạch và tìm các lựa chọn phù hợp cho làn da dễ nổi mụn.',
                'icon': 'fa fa-tint',
                'img': '/beautymatch/static/src/img/concern_acne.webp',
                'link': '/shop?concern=acne_oil',
                'concern_key': 'acne_oil',
            },
            {
                'id': 'dryness',
                'title': 'Da khô',
                'badge': 'Cấp ẩm chuyên sâu',
                'description': 'Khám phá các sản phẩm tập trung vào cấp ẩm và hỗ trợ hàng rào bảo vệ da.',
                'icon': 'fa fa-snowflake-o',
                'img': '/beautymatch/static/src/img/concern_dry.webp',
                'link': '/shop?concern=dryness',
                'concern_key': 'dryness',
            },
            {
                'id': 'sensitivity',
                'title': 'Da nhạy cảm',
                'badge': 'Dịu nhẹ & Phục hồi',
                'description': 'Ưu tiên các lựa chọn dịu nhẹ và thông tin sản phẩm rõ ràng.',
                'icon': 'fa fa-shield',
                'img': '/beautymatch/static/src/img/concern_sensitive.webp',
                'link': '/shop?concern=sensitivity',
                'concern_key': 'sensitivity',
            },
            {
                'id': 'dullness',
                'title': 'Làm sáng',
                'badge': 'Rạng rỡ & Đều màu',
                'description': 'Khám phá các sản phẩm hướng đến nhu cầu cải thiện vẻ ngoài xỉn màu và không đều màu.',
                'icon': 'fa fa-sun-o',
                'img': '/beautymatch/static/src/img/concern_dull.webp',
                'link': '/shop?concern=dullness',
                'concern_key': 'dullness',
            },
        ]
        return request.render('beautymatch.page_theo_van_de_da', {
            'concerns': concerns,
        })

    @http.route(['/beauty-quiz'], type='http', auth='public', methods=['GET', 'POST'], website=True, csrf=False)
    def beauty_quiz(self, **post):
        """Trang Beauty Quiz hỗ trợ cá nhân hóa và gợi ý sản phẩm phù hợp"""
        skin_type = post.get('skin_type')
        concern = post.get('concern')
        routine_type = post.get('routine_type')
        budget = post.get('budget')

        recommended_products = None
        has_submitted = bool(post.get('submitted'))

        if has_submitted:
            domain = [('website_published', '=', True), ('sale_ok', '=', True)]

            # Lọc theo loại da
            if skin_type and skin_type != 'unknown':
                domain.append(('beautymatch_skin_type', 'in', [skin_type, 'all']))

            # Lọc theo vấn đề da
            if concern:
                domain.append(('beautymatch_skin_concern', '=', concern))

            # Lọc theo phân khúc ngân sách
            if budget:
                domain.append(('beautymatch_budget_level', '=', budget))

            ProductTemplate = request.env['product.template'].sudo()
            recommended_products = ProductTemplate.search(
                domain,
                order='beautymatch_is_quiz_recommended desc, beautymatch_is_featured desc, sequence, id desc',
                limit=4,
            )

            # Nếu bộ lọc quá chặt không có sản phẩm, nới lỏng để gợi ý sản phẩm theo loại da hoặc vấn đề da
            if not recommended_products and (skin_type or concern):
                fallback_domain = [('website_published', '=', True), ('sale_ok', '=', True)]
                or_conditions = []
                if skin_type and skin_type != 'unknown':
                    or_conditions.append(('beautymatch_skin_type', 'in', [skin_type, 'all']))
                if concern:
                    or_conditions.append(('beautymatch_skin_concern', '=', concern))

                if or_conditions:
                    if len(or_conditions) > 1:
                        fallback_domain += ['|'] + or_conditions
                    else:
                        fallback_domain += or_conditions

                recommended_products = ProductTemplate.search(
                    fallback_domain,
                    order='beautymatch_is_quiz_recommended desc, sequence, id desc',
                    limit=4,
                )

        return request.render('beautymatch.page_beauty_quiz', {
            'has_submitted': has_submitted,
            'recommended_products': recommended_products,
            'selected_skin_type': skin_type,
            'selected_concern': concern,
            'selected_routine_type': routine_type,
            'selected_budget': budget,
        })

    @http.route('/routine', type='http', auth='public', website=True)
    def routine_guide(self, **kwargs):
        """Trang hướng dẫn quy trình dưỡng da (Skincare Routine) chuẩn khoa học"""
        morning_routine = [
            {
                'step_number': 1,
                'title': 'Làm sạch (Cleanser)',
                'why': 'Loại bỏ dầu thừa và tạp chất tích tụ qua đêm, làm thông thoáng da để hấp thu dưỡng chất.',
                'category_name': 'Sữa rửa mặt',
                'link': '/shop?search=sữa+rửa+mặt',
                'icon': 'fa fa-shower',
            },
            {
                'step_number': 2,
                'title': 'Cân bằng (Toner)',
                'why': 'Cân bằng độ pH tức thì sau khi rửa mặt và cấp ẩm nền cho da.',
                'category_name': 'Toner',
                'link': '/shop?search=toner',
                'icon': 'fa fa-tint',
            },
            {
                'step_number': 3,
                'title': 'Serum',
                'why': 'Cung cấp hoạt chất tập trung nhẹ nhàng ban ngày như Vitamin C, Niacinamide để chống oxy hóa.',
                'category_name': 'Serum',
                'link': '/shop?search=serum',
                'icon': 'fa fa-flask',
            },
            {
                'step_number': 4,
                'title': 'Dưỡng ẩm (Moisturizer)',
                'why': 'Duy trì màng ẩm tự nhiên, bảo vệ da không bị mất nước khi ngồi phòng điều hòa.',
                'category_name': 'Kem dưỡng',
                'link': '/shop?search=kem+dưỡng',
                'icon': 'fa fa-magic',
            },
            {
                'step_number': 5,
                'title': 'Chống nắng (Sunscreen)',
                'why': 'Bước bảo vệ quan trọng nhất ban ngày, ngăn ngừa tia UVA/UVB và lão hóa sớm.',
                'category_name': 'Chống nắng',
                'link': '/shop?search=chống+nắng',
                'icon': 'fa fa-sun-o',
            },
        ]

        evening_routine = [
            {
                'step_number': 1,
                'title': 'Làm sạch kép (Double Cleansing)',
                'why': 'Tẩy trang và rửa sạch hoàn toàn lớp kem chống nắng, bụi mịn và bã nhờn tích tụ cả ngày.',
                'category_name': 'Sữa rửa mặt / Tẩy trang',
                'link': '/shop?search=sữa+rửa+mặt',
                'icon': 'fa fa-shower',
            },
            {
                'step_number': 2,
                'title': 'Cân bằng (Toner)',
                'why': 'Làm dịu làn da mệt mỏi sau ngày dài, tạo điều kiện thẩm thấu dưỡng chất ban đêm.',
                'category_name': 'Toner',
                'link': '/shop?search=toner',
                'icon': 'fa fa-tint',
            },
            {
                'step_number': 3,
                'title': 'Serum / Treatment',
                'why': 'Giai đoạn vàng để tái tạo tế bào, phục hồi da và đặc trị các vấn đề chuyên sâu.',
                'category_name': 'Serum / Treatment',
                'link': '/shop?search=serum',
                'icon': 'fa fa-flask',
            },
            {
                'step_number': 4,
                'title': 'Dưỡng ẩm ban đêm (Night Cream)',
                'why': 'Khóa chặt các lớp dưỡng chất và hỗ trợ phục hồi hàng rào bảo vệ da trong lúc ngủ.',
                'category_name': 'Kem dưỡng',
                'link': '/shop?search=kem+dưỡng',
                'icon': 'fa fa-moon-o',
            },
        ]

        return request.render('beautymatch.page_routine', {
            'morning_routine': morning_routine,
            'evening_routine': evening_routine,
        })

    @http.route('/brands', type='http', auth='public', website=True)
    def brands(self, **kwargs):
        """Trang danh sách thương hiệu phân phối tại BeautyMatch"""
        brands_data = []

        # 1. Ưu tiên lấy danh sách thương hiệu từ các sản phẩm BeautyMatch đang xuất bản
        ProductTemplate = request.env['product.template'].sudo()
        products_with_brand = ProductTemplate.search([
            ('website_published', '=', True),
            ('beautymatch_brand', '!=', False),
        ])
        distinct_brands = sorted(list({p.beautymatch_brand.strip() for p in products_with_brand if p.beautymatch_brand}))

        if distinct_brands:
            for idx, bname in enumerate(distinct_brands, start=1):
                brands_data.append({
                    'id': idx,
                    'name': bname,
                    'link': f'/shop?brand={bname}',
                })
        else:
            # 2. Fallback nếu dùng thuộc tính product.attribute
            Attribute = request.env['product.attribute'].sudo()
            brand_attr = Attribute.search([('name', 'ilike', 'brand')], limit=1)
            if not brand_attr:
                brand_attr = Attribute.search([('name', 'ilike', 'thương hiệu')], limit=1)

            if brand_attr and brand_attr.value_ids:
                for val in brand_attr.value_ids:
                    brands_data.append({
                        'id': val.id,
                        'name': val.name,
                        'link': f'/shop?attrib={brand_attr.id}-{val.id}',
                    })

        return request.render('beautymatch.page_brands', {
            'brands': brands_data,
        })
