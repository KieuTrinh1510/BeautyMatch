# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# mypy: ignore-errors
import logging

# pyrefly: ignore[missing-import]
from odoo import http, fields  # type: ignore
# pyrefly: ignore[missing-import]
from odoo.http import request  # type: ignore
# pyrefly: ignore[missing-import]
from odoo.fields import Domain  # type: ignore
# pyrefly: ignore[missing-import]
from odoo.addons.website.controllers.main import Website  # type: ignore
# pyrefly: ignore[missing-import]
from odoo.addons.website_sale.controllers.main import WebsiteSale  # type: ignore
# pyrefly: ignore[missing-import]
from odoo.addons.website_sale.controllers.cart import Cart  # type: ignore
from odoo.tools.translate import _lt  # type: ignore

_logger = logging.getLogger(__name__)


class BeautyMatchWebsite(Website):

    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def index(self, **kw):
        """Trang chủ chuyên biệt của BeautyMatch (Dedicated Homepage)"""
        ProductTemplate = request.env['product.template'].sudo()
        # Lấy 10 sản phẩm nổi bật được cấu hình beautymatch_is_featured (2 hàng x 5 sản phẩm)
        featured_products = ProductTemplate.search([
            ('website_published', '=', True),
            ('sale_ok', '=', True),
            ('beautymatch_is_featured', '=', True),
        ], limit=10, order='sequence, id desc')

        return request.render('beautymatch.homepage', {
            'featured_products': featured_products,
        })

    @http.route(['/beautymatch/cart/add', '/shop/cart/bm_add'], type='http', auth='public', methods=['POST', 'GET'], website=True, sitemap=False, csrf=False)
    def quick_add_to_cart(self, product_id=None, quantity=1, redirect_to='/shop/cart', **kw):
        """Thêm nhanh sản phẩm vào giỏ hàng qua HTTP (hỗ trợ cả form POST truyền thống lẫn AJAX)."""
        if not product_id:
            return request.redirect('/shop')
        try:
            product_id = int(product_id)
            quantity = int(quantity or 1)
        except (ValueError, TypeError):
            return request.redirect('/shop')

        order_sudo = request.cart or request.website._create_cart()
        if request.session.get('bm_retained_cart_id'):
            retained_id = request.session.get('bm_retained_cart_id')
            retained_order = request.env['sale.order'].sudo().browse(retained_id).exists()
            if retained_order and retained_order.state == 'draft':
                if order_sudo and order_sudo.id != retained_order.id:
                    for line in retained_order.order_line:
                        line.write({'order_id': order_sudo.id, 'bm_is_selected': False})
                    retained_order.sudo().unlink()
                    request.session.pop('bm_retained_cart_id', None)
            else:
                request.session.pop('bm_retained_cart_id', None)

        product = request.env['product.product'].sudo().browse(product_id).exists()
        if product and product.sale_ok:
            order_sudo.with_context(skip_cart_verification=True)._cart_add(
                product_id=product.id,
                quantity=quantity,
            )
            request.session['website_sale_cart_quantity'] = int(order_sudo.cart_quantity)

        # Nếu là AJAX request
        if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest' or kw.get('ajax'):
            import json
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'cart_quantity': int(order_sudo.cart_quantity),
                    'product_name': product.name if product else '',
                }),
                headers=[('Content-Type', 'application/json')]
            )

        return request.redirect(redirect_to or '/shop/cart')


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
            budget_conds = []
            for bg in budgets:
                if bg == 'budget':
                    budget_conds.append(Domain('list_price', '<=', 250000))
                    budget_conds.append(Domain('beautymatch_budget_level', '=', 'budget'))
                elif bg == 'mid':
                    budget_conds.append(Domain.AND([Domain('list_price', '>', 250000), Domain('list_price', '<=', 500000)]))
                    budget_conds.append(Domain('beautymatch_budget_level', '=', 'mid'))
                elif bg == 'high':
                    budget_conds.append(Domain.AND([Domain('list_price', '>', 500000), Domain('list_price', '<=', 1000000)]))
                elif bg == 'premium':
                    budget_conds.append(Domain('list_price', '>', 1000000))
                    budget_conds.append(Domain('beautymatch_budget_level', '=', 'premium'))
                else:
                    budget_conds.append(Domain('beautymatch_budget_level', '=', bg))
            if budget_conds:
                extra_domains.append(Domain.OR(budget_conds))

        # 6. Lọc theo Dung tích
        volumes = req_args.getlist('volume')
        if volumes:
            vol_conds = []
            for vol in volumes:
                if vol == 'lt50':
                    vol_conds.extend([Domain('beautymatch_volume', 'ilike', v) for v in ['20ml', '30ml', '40ml']])
                elif vol == '50_100':
                    vol_conds.extend([Domain('beautymatch_volume', 'ilike', v) for v in ['50ml', '50g', '60ml', '100ml']])
                elif vol == '100_200':
                    vol_conds.extend([Domain('beautymatch_volume', 'ilike', v) for v in ['110g', '150ml', '170ml', '180ml', '200ml']])
                elif vol == 'gt200':
                    vol_conds.extend([Domain('beautymatch_volume', 'ilike', v) for v in ['236ml', '340g', '355ml', '400ml', '473ml']])
                else:
                    vol_conds.append(Domain('beautymatch_volume', 'ilike', vol))
            if vol_conds:
                extra_domains.append(Domain.OR(vol_conds))

        if extra_domains:
            domain = Domain.AND([domain] + extra_domains)

        return domain

    def _shop_get_query_url_kwargs(self, search, min_price, max_price, **post):
        kwargs = super()._shop_get_query_url_kwargs(search, min_price, max_price, **post)
        req_args = request.httprequest.args
        for param in ['skin_type', 'concern', 'brand', 'ingredient', 'budget', 'volume', 'order']:
            val = req_args.getlist(param)
            if val:
                kwargs[param] = val if len(val) > 1 else val[0]
        return kwargs

    def _get_search_options(self, **post):
        options = super()._get_search_options(**post)
        req_args = request.httprequest.args
        for param in ['skin_type', 'concern', 'brand', 'ingredient', 'budget', 'volume', 'order']:
            val = req_args.getlist(param)
            if val:
                options[param] = val
        if req_args.get('min_price'):
            try:
                options['bm_raw_min_price'] = float(req_args.get('min_price'))
            except (ValueError, TypeError):
                pass
        if req_args.get('max_price'):
            try:
                options['bm_raw_max_price'] = float(req_args.get('max_price'))
            except (ValueError, TypeError):
                pass
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
                ('high', 'Cao cấp (500k - 1tr)'),
                ('premium', 'Premium (> 1tr)'),
            ]

            volume_options = [
                ('lt50', 'Dưới 50ml'),
                ('50_100', '50 – 100ml'),
                ('100_200', '100 – 200ml'),
                ('gt200', 'Trên 200ml'),
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
                'Rau má',
                'Vitamin C',
            ]

            # Dung tích thực tế của sản phẩm
            available_volumes = sorted(list({
                p.beautymatch_volume.strip() for p in published_products if p.beautymatch_volume
            }))

            active_filter_count = (
                len(selected_skin_types)
                + len(selected_concerns)
                + len(selected_brands)
                + len(selected_ingredients)
                + len(selected_budgets)
                + len(selected_volumes)
                + (1 if req_args.get('min_price') or (req_args.get('max_price') and float(req_args.get('max_price', 0)) < 1500000) else 0)
            )

            has_active_bm_filters = bool(active_filter_count > 0 or category)

            response.qcontext.update({
                'bm_main_categories': main_categories,
                'bm_skin_types_data': skin_types_data,
                'bm_skin_concerns_data': skin_concerns_data,
                'bm_budget_levels_data': budget_levels_data,
                'bm_volume_options': volume_options,
                'bm_available_brands': available_brands,
                'bm_popular_ingredients': popular_ingredients,
                'bm_available_volumes': available_volumes,
                'bm_selected_skin_types': selected_skin_types,
                'bm_selected_concerns': selected_concerns,
                'bm_selected_brands': selected_brands,
                'bm_selected_ingredients': selected_ingredients,
                'bm_selected_budgets': selected_budgets,
                'bm_selected_volumes': selected_volumes,
                'bm_active_filter_count': active_filter_count,
                'bm_has_active_filters': has_active_bm_filters,
                'bm_min_price': float(req_args.get('min_price') or 0),
                'bm_max_price': float(req_args.get('max_price') or 1500000),
            })

        return response

    @http.route(['/shop/<model("product.template"):product>'], type='http', auth="public", website=True, sitemap=True)
    def product(self, product, category='', search='', **kwargs):
        """Theo dõi sản phẩm đã xem gần đây (Recently Viewed) trong session"""
        if product and product.exists():
            curr_id = product.id
            recent_ids = list(request.session.get('bm_recently_viewed') or [])
            if curr_id in recent_ids:
                recent_ids.remove(curr_id)
            recent_ids.insert(0, curr_id)
            request.session['bm_recently_viewed'] = recent_ids[:10]
            request.session.touch()

        return super().product(product, category=category, search=search, **kwargs)

    @http.route(
        '/shop/checkout', type='http', methods=['GET', 'POST'], auth='public', website=True, sitemap=False
    )
    def shop_checkout(self, try_skip_step=None, **query_params):
        """Chuyển hướng thông minh đến trang thanh toán thống nhất Shopee-style (/shop/payment).
        Chỉ thanh toán các sản phẩm được tích chọn (bm_is_selected=True).
        Các sản phẩm không chọn được bảo toàn sang retained_order để giữ lại trong giỏ hàng.
        """
        order_sudo = request.cart
        if not order_sudo or not order_sudo.order_line:
            return request.redirect('/shop/cart')

        prod_lines = order_sudo.order_line.filtered(
            lambda l: not l.is_reward_line and not l.is_delivery and not l.reward_id
        )
        selected_lines = prod_lines.filtered('bm_is_selected')
        unselected_lines = prod_lines.filtered(lambda l: not l.bm_is_selected)

        # 1. Nếu không có sản phẩm nào được chọn -> quay lại giỏ hàng
        if not selected_lines:
            return request.redirect('/shop/cart')

        # 2. Nếu có sản phẩm KHÔNG chọn -> tách sang retained_order để bảo toàn trong giỏ
        if unselected_lines:
            retained_order = False
            if request.session.get('bm_retained_cart_id'):
                retained_order = request.env['sale.order'].sudo().browse(request.session['bm_retained_cart_id']).exists()
                if not retained_order or retained_order.state != 'draft':
                    retained_order = False

            if not retained_order:
                retained_order = request.env['sale.order'].sudo().create({
                    'partner_id': order_sudo.partner_id.id,
                    'partner_invoice_id': order_sudo.partner_invoice_id.id,
                    'partner_shipping_id': order_sudo.partner_shipping_id.id,
                    'pricelist_id': order_sudo.pricelist_id.id,
                    'company_id': order_sudo.company_id.id,
                    'website_id': order_sudo.website_id.id,
                    'team_id': order_sudo.team_id.id,
                    'state': 'draft',
                    'bm_is_retained_cart': True,
                })

            unselected_lines.write({'order_id': retained_order.id})
            request.session['bm_retained_cart_id'] = retained_order.id

        # 3. Dọn dẹp voucher / rewards cũ để tính toán mới chính xác trên các sản phẩm đã chọn
        order_sudo._clean_beautymatch_rewards()
        order_sudo._recompute_prices()

        request.session['sale_last_order_id'] = order_sudo.id

        if redirection := self._check_cart(order_sudo):
            return redirection

        return request.redirect('/shop/payment')

    def _check_addresses(self, order_sudo):
        """Cho phép vào thẳng /shop/payment để khách hàng xem và cập nhật địa chỉ trực tiếp trên modal"""
        return None

    @http.route('/shop/payment', type='http', auth='public', website=True, sitemap=False, list_as_website_content=_lt("Shop Payment"))
    def shop_payment(self, **post):
        """Trang thanh toán BeautyMatch.
        Kiểm tra backend nghiêm ngặt:
        1. Phải có ít nhất 1 sản phẩm được chọn (bm_is_selected=True).
        2. Nếu 0 sản phẩm được chọn -> chặn truy cập, chuyển hướng về /shop/cart (TC08).
        3. Nếu có sản phẩm chưa chọn nhưng chưa được tách (do khách vào thẳng /shop/payment) -> tách sang retained_order.
        """
        order_sudo = request.cart
        if not order_sudo or not order_sudo.order_line:
            return request.redirect('/shop/cart')

        prod_lines = order_sudo.order_line.filtered(
            lambda l: not l.is_reward_line and not l.is_delivery and not l.reward_id
        )
        selected_lines = prod_lines.filtered('bm_is_selected')
        unselected_lines = prod_lines.filtered(lambda l: not l.bm_is_selected)

        # 1. Chặn truy cập nếu không có sản phẩm nào được chọn
        if not selected_lines:
            return request.redirect('/shop/cart')

        # 2. Nếu có sản phẩm chưa chọn -> tách sang retained_order
        if unselected_lines:
            retained_order = False
            if request.session.get('bm_retained_cart_id'):
                retained_order = request.env['sale.order'].sudo().browse(request.session['bm_retained_cart_id']).exists()
                if not retained_order or retained_order.state != 'draft':
                    retained_order = False

            if not retained_order:
                retained_order = request.env['sale.order'].sudo().create({
                    'partner_id': order_sudo.partner_id.id,
                    'partner_invoice_id': order_sudo.partner_invoice_id.id,
                    'partner_shipping_id': order_sudo.partner_shipping_id.id,
                    'pricelist_id': order_sudo.pricelist_id.id,
                    'company_id': order_sudo.company_id.id,
                    'website_id': order_sudo.website_id.id,
                    'team_id': order_sudo.team_id.id,
                    'state': 'draft',
                    'bm_is_retained_cart': True,
                })

            unselected_lines.write({'order_id': retained_order.id})
            request.session['bm_retained_cart_id'] = retained_order.id
            order_sudo._clean_beautymatch_rewards()
            order_sudo._recompute_prices()

        return super().shop_payment(**post)

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False, list_as_website_content=_lt("Shop Confirmation"))
    def shop_payment_confirmation(self, **post):
        """Xác nhận đơn hàng và kích hoạt lại các sản phẩm chưa thanh toán vào giỏ hàng"""
        res = super().shop_payment_confirmation(**post)

        if request.session.get('bm_retained_cart_id'):
            retained_id = request.session.pop('bm_retained_cart_id')
            retained_order = request.env['sale.order'].sudo().browse(retained_id).exists()
            if retained_order and retained_order.state == 'draft':
                request.session['sale_order_id'] = retained_order.id
                request.session['website_sale_cart_quantity'] = retained_order.cart_quantity
                request.cart = retained_order
                retained_order.order_line.write({'bm_is_selected': True})

        return res

    def _get_shop_payment_values(self, order, **kwargs):
        values = super()._get_shop_payment_values(order, **kwargs)

        values['submit_button_label'] = 'Đặt hàng'
        values['bm_voucher_info'] = order._get_beautymatch_voucher_summary()

        if order._has_deliverable_products():
            available_dms = order._get_delivery_methods()
            values['delivery_methods'] = available_dms
            if not order.carrier_id and available_dms:
                preferred = order._get_preferred_delivery_method(available_dms) or available_dms[0]
                rate = preferred.rate_shipment(order)
                order._set_delivery_method(preferred, rate=rate)

        partner_sudo = order.partner_id
        is_public = request.website.is_public_user()
        if partner_sudo and not is_public:
            commercial = partner_sudo.commercial_partner_id
            addrs = request.env['res.partner'].sudo().search([
                '|',
                ('id', '=', commercial.id),
                ('parent_id', '=', commercial.id),
            ], order='bm_is_default_shipping desc, id desc')
            valid_addrs = addrs.filtered(lambda a: a.type in ('delivery', 'contact') and a.active)
            if valid_addrs and not any(a.bm_is_default_shipping for a in valid_addrs):
                default_target = valid_addrs.filtered(lambda a: a.id == commercial.id) or valid_addrs[0]
                default_target.sudo().write({'bm_is_default_shipping': True})
            values['delivery_addresses'] = valid_addrs or commercial
            # Đảm bảo đơn hàng trỏ tới một địa chỉ giao hàng hợp lệ
            if not order.partner_shipping_id or (valid_addrs and order.partner_shipping_id not in valid_addrs):
                default_addr = valid_addrs.filtered(lambda a: a.bm_is_default_shipping) or valid_addrs[0]
                order.sudo().write({'partner_shipping_id': default_addr.id})
        else:
            values['delivery_addresses'] = order.partner_shipping_id or order.partner_id

        return values

    @http.route('/shop/beautymatch/apply_voucher', type='jsonrpc', auth='public', website=True)
    def beautymatch_apply_voucher(self, code=None, **kwargs):
        """Áp dụng hoặc gỡ bỏ 1 trong 2 voucher BeautyMatch (WELCOME10 / BEAUTY50)"""
        order_sudo = request.cart
        if not order_sudo:
            return {'error': 'Không tìm thấy thông tin giỏ hàng.'}

        result = order_sudo._apply_beautymatch_single_voucher(code)
        if result.get('error'):
            return result

        v_info = order_sudo._get_beautymatch_voucher_summary()
        amount_delivery_formatted = 'Miễn phí' if order_sudo.amount_delivery == 0.0 else f"{order_sudo.amount_delivery:,.0f} ₫"
        reward_formatted = f"-{v_info['reward_amount']:,.0f} ₫" if v_info['reward_amount'] > 0 else "0 ₫"

        return {
            'success': True,
            'applied_code': v_info['applied_code'],
            'reward_amount': reward_formatted,
            'has_reward': (v_info['reward_amount'] > 0),
            'amount_untaxed': f"{order_sudo.amount_untaxed:,.0f} ₫",
            'amount_delivery': amount_delivery_formatted,
            'is_delivery_free': (order_sudo.amount_delivery == 0.0),
            'amount_total': f"{order_sudo.amount_total:,.0f} ₫",
            'vouchers': v_info['vouchers'],
        }

    @http.route('/shop/beautymatch/update_shipping_address', type='jsonrpc', auth='public', website=True)
    def beautymatch_update_shipping_address(self, partner_id=None, **kwargs):
        """Chọn địa chỉ nhận hàng cho đơn hàng hiện tại"""
        order_sudo = request.cart
        if not order_sudo:
            return {'error': 'Không tìm thấy giỏ hàng.'}

        if not partner_id:
            return {'error': 'Mã địa chỉ không hợp lệ.'}

        partner_sudo = request.env['res.partner'].sudo().browse(int(partner_id)).exists()
        if not partner_sudo:
            return {'error': 'Không tìm thấy địa chỉ được chọn.'}

        order_sudo.sudo().write({'partner_shipping_id': partner_sudo.id})

        if order_sudo.carrier_id:
            try:
                rate = order_sudo.carrier_id.rate_shipment(order_sudo)
                if rate.get('success'):
                    order_sudo.set_delivery_line(order_sudo.carrier_id, rate['price'])
            except Exception as e:
                _logger.warning("Error re-rating shipment: %s", e)
        order_sudo._update_programs_and_rewards()

        return {'success': True}

    @http.route('/shop/beautymatch/save_address', type='jsonrpc', auth='public', website=True)
    def beautymatch_save_address(self, address_id=None, name='', phone='', street='', city=None, email=None, is_default=False, **kwargs):
        """Lưu (tạo mới hoặc cập nhật) địa chỉ nhận hàng theo phong cách Shopee"""
        order_sudo = request.cart
        if not order_sudo:
            return {'error': 'Không tìm thấy giỏ hàng.'}

        name = (name or '').strip()
        phone = (phone or '').strip()
        street = (street or '').strip()
        city = (city or 'Hà Nội').strip()
        email = (email or '').strip()

        if not name or not phone or not street:
            return {'error': 'Vui lòng điền đầy đủ Họ tên, Số điện thoại và Địa chỉ cụ thể.'}

        commercial = order_sudo.partner_id.commercial_partner_id
        is_public = request.website.is_public_user()

        if address_id:
            # Chế độ Sửa địa chỉ có sẵn
            target = request.env['res.partner'].sudo().browse(int(address_id)).exists()
            if not target:
                return {'error': 'Không tìm thấy địa chỉ cần sửa.'}
            update_vals = {
                'name': name,
                'phone': phone,
                'street': street,
                'city': city,
            }
            if email:
                update_vals['email'] = email
            target.write(update_vals)
            partner = target
        else:
            # Chế độ Thêm địa chỉ mới
            if is_public or not commercial:
                partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'phone': phone,
                    'street': street,
                    'city': city,
                    'email': email,
                    'type': 'delivery',
                })
                order_sudo.sudo().write({
                    'partner_id': partner.id,
                    'partner_invoice_id': partner.id,
                })
            else:
                partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'phone': phone,
                    'street': street,
                    'city': city,
                    'email': email or commercial.email or '',
                    'type': 'delivery',
                    'parent_id': commercial.id,
                })

        # Đặt làm địa chỉ mặc định nếu người dùng chọn
        if is_default:
            partner.bm_set_as_default_shipping()

        # Luôn đặt địa chỉ vừa lưu làm địa chỉ giao hàng cho đơn hiện tại
        order_sudo.sudo().write({'partner_shipping_id': partner.id})

        if order_sudo.carrier_id:
            try:
                rate = order_sudo.carrier_id.rate_shipment(order_sudo)
                if rate.get('success'):
                    order_sudo.set_delivery_line(order_sudo.carrier_id, rate['price'])
            except Exception as e:
                _logger.warning("Error re-rating shipment: %s", e)
        order_sudo._update_programs_and_rewards()

        return {'success': True, 'address_id': partner.id}

    @http.route('/shop/beautymatch/set_default_address', type='jsonrpc', auth='public', website=True)
    def beautymatch_set_default_address(self, address_id, **kwargs):
        """Đặt một địa chỉ làm địa chỉ nhận hàng mặc định của tài khoản"""
        if not address_id:
            return {'error': 'Mã địa chỉ không hợp lệ.'}
        target = request.env['res.partner'].sudo().browse(int(address_id)).exists()
        if not target:
            return {'error': 'Không tìm thấy địa chỉ.'}
        target.bm_set_as_default_shipping()

        order_sudo = request.cart
        if order_sudo:
            order_sudo.sudo().write({'partner_shipping_id': target.id})
            if order_sudo.carrier_id:
                try:
                    rate = order_sudo.carrier_id.rate_shipment(order_sudo)
                    if rate.get('success'):
                        order_sudo.set_delivery_line(order_sudo.carrier_id, rate['price'])
                except Exception as e:
                    _logger.warning("Error re-rating shipment: %s", e)
            order_sudo._update_programs_and_rewards()

        return {'success': True}


class BeautyMatchCart(Cart):
    """Mở rộng giỏ hàng BeautyMatch hỗ trợ chọn sản phẩm thanh toán kiểu Shopee"""

    def _restore_retained_cart(self):
        """Khôi phục các sản phẩm retained cart nếu khách quay lại từ checkout"""
        if request.session.get('bm_retained_cart_id'):
            retained_id = request.session.get('bm_retained_cart_id')
            retained_order = request.env['sale.order'].sudo().browse(retained_id).exists()
            if retained_order and retained_order.state == 'draft':
                order = request.cart
                if order and order.state == 'draft' and order.id != retained_order.id:
                    for line in retained_order.order_line:
                        line.write({'order_id': order.id, 'bm_is_selected': False})
                    retained_order.sudo().unlink()
                    request.session.pop('bm_retained_cart_id', None)
                    order._clean_beautymatch_rewards()
                    order._recompute_prices()
            else:
                request.session.pop('bm_retained_cart_id', None)

    @http.route(route='/shop/cart', type='http', auth='public', website=True, sitemap=False)
    def cart(self, id=None, access_token=None, revive_method='', **post):
        """Trang giỏ hàng BeautyMatch. Khôi phục các sản phẩm retained cart nếu khách quay lại từ checkout"""
        self._restore_retained_cart()
        res = super().cart(id=id, access_token=access_token, revive_method=revive_method, **post)
        if hasattr(res, 'qcontext'):
            res.qcontext['hide_promotions'] = True
        return res

    @http.route(
        route='/shop/cart/update',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        sitemap=False
    )
    def update_cart(self, line_id, quantity, product_id=None, **kwargs):
        """Cập nhật số lượng sản phẩm trong giỏ hàng. Bảo toàn trạng thái chọn và cập nhật số liệu chuẩn"""
        values = super().update_cart(line_id, quantity, product_id=product_id, **kwargs)
        order = request.cart
        if order:
            prod_lines = order.order_line.filtered(
                lambda l: not l.is_reward_line and not l.is_delivery and not l.reward_id
            )
            selected_lines = prod_lines.filtered('bm_is_selected')
            selected_count = len(selected_lines)
            total_count = len(prod_lines)
            all_selected = bool(prod_lines and selected_count == total_count)
            currency = order.currency_id

            selected_subtotal = sum(l.price_subtotal for l in selected_lines)
            selected_tax = sum(l.price_tax for l in selected_lines)
            selected_total = sum(l.price_total for l in selected_lines)

            values['selected_count'] = selected_count
            values['total_count'] = total_count
            values['all_selected'] = all_selected
            values['selected_subtotal'] = selected_subtotal
            values['selected_subtotal_formatted'] = currency.format(selected_subtotal) if currency else f"{selected_subtotal:,.0f} ₫"
            values['selected_tax'] = selected_tax
            values['selected_tax_formatted'] = currency.format(selected_tax) if currency else f"{selected_tax:,.0f} ₫"
            values['selected_total'] = selected_total
            values['selected_total_formatted'] = currency.format(selected_total) if currency else f"{selected_total:,.0f} ₫"
        return values

    @http.route('/shop/cart/update_selection', type='jsonrpc', auth='public', website=True)
    def cart_update_selection(self, line_id=None, selected=None, select_all=None, **kw):
        """Cập nhật trạng thái chọn sản phẩm trong giỏ hàng (Shopee style)"""
        order = request.cart
        if not order:
            return {'error': 'Không tìm thấy giỏ hàng.'}

        prod_lines = order.order_line.filtered(
            lambda l: not l.is_reward_line and not l.is_delivery and not l.reward_id
        )

        if select_all is not None:
            prod_lines.write({'bm_is_selected': bool(select_all)})
        elif line_id is not None:
            target_line = prod_lines.filtered(lambda l: l.id == int(line_id))
            if target_line:
                target_line.write({'bm_is_selected': bool(selected)})

        selected_lines = prod_lines.filtered('bm_is_selected')
        selected_count = len(selected_lines)
        total_count = len(prod_lines)
        all_selected = bool(prod_lines and selected_count == total_count)

        selected_subtotal = sum(l.price_subtotal for l in selected_lines)
        selected_tax = sum(l.price_tax for l in selected_lines)
        selected_total = sum(l.price_total for l in selected_lines)

        currency = order.currency_id
        subtotal_formatted = currency.format(selected_subtotal) if currency else f"{selected_subtotal:,.0f} ₫"
        tax_formatted = currency.format(selected_tax) if currency else f"{selected_tax:,.0f} ₫"
        total_formatted = currency.format(selected_total) if currency else f"{selected_total:,.0f} ₫"

        return {
            'success': True,
            'selected_count': selected_count,
            'total_count': total_count,
            'selected_subtotal': selected_subtotal,
            'selected_subtotal_formatted': subtotal_formatted,
            'selected_tax': selected_tax,
            'selected_tax_formatted': tax_formatted,
            'selected_total': selected_total,
            'selected_total_formatted': total_formatted,
            'all_selected': all_selected,
        }



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


class BeautyMatchOrderController(http.Controller):

    @http.route(['/shop/order/reorder/<int:order_id>'], type='http', auth='public', website=True)
    def beautymatch_reorder(self, order_id, access_token=None, **kw):
        """1-Click Reorder logic for BeautyMatch customers.
        - Gets real sellable product lines from the specified order.
        - Skips delivery lines and coupon/reward lines.
        - Does NOT copy old discounts, prices, or shipping fees.
        - Checks that products are active, sellable, and published.
        - Uses the CURRENT active price in the website cart.
        - Adds items to the customer's cart and redirects to /shop/cart.
        """
        try:
            order_sudo = request.env['sale.order'].sudo().browse(order_id).exists()
            if not order_sudo:
                return request.redirect('/shop/cart')
        except Exception:
            return request.redirect('/shop/cart')

        # Check access permission: public with access_token or matching user or internal user
        user = request.env.user
        if not user.has_group('base.group_user') and order_sudo.partner_id != user.partner_id:
            if not access_token or access_token != order_sudo.access_token:
                return request.redirect('/my/orders')

        lines_to_add = order_sudo.order_line.filtered(
            lambda l: not l.is_delivery
            and not l.reward_id
            and not l.is_reward_line
            and not l.display_type
            and l.product_id
            and l.product_id.active
            and l.product_id.sale_ok
            and l.product_id.is_published
        )

        if not lines_to_add:
            return request.redirect('/shop/cart')

        Cart_controller = Cart()
        for line in lines_to_add:
            try:
                Cart_controller.add_to_cart(
                    product_id=line.product_id.id,
                    product_template_id=line.product_id.product_tmpl_id.id,
                    quantity=line.product_uom_qty,
                )
            except Exception:
                pass

        return request.redirect('/shop/cart')


class BeautyMatchTrustController(http.Controller):

    @http.route('/about', type='http', auth='public', website=True, sitemap=True)
    def beautymatch_about(self, **kw):
        """1. Giới thiệu BeautyMatch (/about): Nền tảng skincare khoa học, 5 tiêu chí cá nhân hóa, không claim y tế"""
        return request.render('beautymatch.page_about', {})

    @http.route('/shipping-policy', type='http', auth='public', website=True, sitemap=True)
    def beautymatch_shipping_policy(self, **kw):
        """2. Chính sách giao hàng (/shipping-policy): Tiêu chuẩn 30k, freeship từ 500k sau coupon, tracking 5 bước"""
        return request.render('beautymatch.page_shipping_policy', {})

    @http.route('/return-policy', type='http', auth='public', website=True, sitemap=True)
    def beautymatch_return_policy(self, **kw):
        """3. Chính sách đổi trả (/return-policy): Tiếp nhận lỗi giao hàng, hư hỏng, thiếu hàng; điều kiện 48h"""
        return request.render('beautymatch.page_return_policy', {})

    @http.route('/payment-policy', type='http', auth='public', website=True, sitemap=True)
    def beautymatch_payment_policy(self, **kw):
        """4. Chính sách thanh toán (/payment-policy): Đúng 2 phương thức COD & Chuyển khoản (MB Bank demo)"""
        return request.render('beautymatch.page_payment_policy', {})

    @http.route('/privacy-policy', type='http', auth='public', website=True, sitemap=True)
    def beautymatch_privacy_policy(self, **kw):
        """5. Chính sách bảo mật (/privacy-policy): Dữ liệu thu thập & mục đích, cam kết không bán dữ liệu"""
        return request.render('beautymatch.page_privacy_policy', {})

    @http.route('/faq', type='http', auth='public', website=True, sitemap=True)
    def beautymatch_faq(self, **kw):
        """6. Câu hỏi thường gặp (/faq): Accordion 14 câu hỏi chuẩn xác theo tính năng hệ thống"""
        return request.render('beautymatch.page_faq', {})

    @http.route(['/contact', '/contactus'], type='http', auth='public', methods=['GET', 'POST'], website=True, csrf=True, sitemap=True)
    def beautymatch_contact(self, **post):
        """7. Liên hệ (/contact): Tiếp nhận yêu cầu tư vấn, lưu trữ an toàn qua res.partner & log chatter"""
        submitted = False
        default_name = ''
        default_email = ''
        default_phone = ''

        user = request.env.user
        if not user._is_public():
            partner = user.partner_id
            default_name = partner.name or ''
            default_email = partner.email or ''
            default_phone = partner.phone or ''

        if request.httprequest.method == 'POST':
            name = (post.get('name') or '').strip()
            email = (post.get('email') or '').strip()
            phone = (post.get('phone') or '').strip()
            subject = (post.get('subject') or 'Tư vấn chung').strip()
            message = (post.get('message') or '').strip()

            if name and (email or phone or message):
                try:
                    PartnerSudo = request.env['res.partner'].sudo()
                    target_partner = False
                    if email:
                        target_partner = PartnerSudo.search([('email', '=', email)], limit=1)
                    if not target_partner and not user._is_public():
                        target_partner = user.partner_id.sudo()

                    inquiry_note = (
                        f"[BeautyMatch Contact - {fields.Datetime.now()}]\n"
                        f"Họ tên: {name}\n"
                        f"Email: {email}\n"
                        f"SĐT: {phone}\n"
                        f"Chủ đề: {subject}\n"
                        f"Nội dung: {message}\n"
                    )

                    if target_partner:
                        old_comment = target_partner.comment or ''
                        target_partner.write({
                            'comment': f"{old_comment}\n\n{inquiry_note}" if old_comment else inquiry_note,
                            'phone': phone or target_partner.phone,
                        })
                    else:
                        target_partner = PartnerSudo.create({
                            'name': name,
                            'email': email,
                            'phone': phone,
                            'comment': inquiry_note,
                        })

                    # Ghi nhận nội bộ vào chatter nếu model hỗ trợ (an toàn tuyệt đối, không kích hoạt gửi mail SMTP ra ngoài)
                    try:
                        if hasattr(target_partner, 'message_post'):
                            target_partner.message_post(
                                body=(
                                    f"<p><b>Yêu cầu liên hệ mới từ BeautyMatch Website</b></p>"
                                    f"<p><b>Chủ đề:</b> {subject}</p>"
                                    f"<p><b>SĐT:</b> {phone}</p>"
                                    f"<p><b>Nội dung:</b><br/>{message}</p>"
                                ),
                                subject=f"[BeautyMatch Liên Hệ] {subject}",
                                subtype_xmlid='mail.mt_note',
                            )
                    except Exception:
                        pass

                    submitted = True
                except Exception as e:
                    _logger.warning("Error saving contact request: %s", e)
                    submitted = True

        return request.render('beautymatch.page_contact', {
            'submitted': submitted,
            'default_name': default_name,
            'default_email': default_email,
            'default_phone': default_phone,
        })


class BeautyMatchCompareController(http.Controller):
    """Bộ điều khiển tính năng So Sánh Sản Phẩm BeautyMatch (/compare).
    - Lưu danh sách so sánh trong session (hỗ trợ cả khách vãng lai và thành viên).
    - Giới hạn tối đa 3 sản phẩm.
    - Highlight khác biệt và gợi ý 'Phù hợp hơn nếu bạn...' chuẩn khoa học.
    """

    def _get_compare_product_ids(self):
        ids = request.session.get('bm_compare_product_ids') or []
        valid_ids = []
        for x in ids:
            try:
                valid_ids.append(int(x))
            except (ValueError, TypeError):
                pass
        return valid_ids[:3]

    def _set_compare_product_ids(self, ids):
        request.session['bm_compare_product_ids'] = ids[:3]

    def _get_compare_data(self):
        product_ids = self._get_compare_product_ids()
        products = request.env['product.template'].sudo().browse(product_ids).filtered(
            lambda p: p.exists() and p.website_published
        )
        if len(products.ids) != len(product_ids):
            self._set_compare_product_ids(products.ids)
            product_ids = products.ids

        website = request.website
        products_prices = products._get_sales_prices(website) if hasattr(products, '_get_sales_prices') else {}

        items = []
        for p in products:
            p_price = products_prices.get(p.id, {}).get('price_reduce', p.list_price)
            items.append({
                'id': p.id,
                'name': p.name,
                'image_url': f'/web/image/product.template/{p.id}/image_1920/200x200',
                'brand': p.beautymatch_brand or 'BeautyMatch',
                'price': p_price,
            })
        return {
            'count': len(product_ids),
            'product_ids': product_ids,
            'products': items,
        }

    @http.route('/shop/compare/get', type='jsonrpc', auth='public', website=True)
    def compare_get(self, **kw):
        return self._get_compare_data()

    @http.route('/shop/compare/toggle', type='jsonrpc', auth='public', website=True)
    def compare_toggle(self, product_id, **kw):
        try:
            p_id = int(product_id)
        except (ValueError, TypeError):
            return {'status': 'error', 'message': 'Invalid product ID'}

        curr_ids = self._get_compare_product_ids()
        if p_id in curr_ids:
            curr_ids.remove(p_id)
            self._set_compare_product_ids(curr_ids)
            data = self._get_compare_data()
            data['status'] = 'removed'
            return data

        if len(curr_ids) >= 3:
            data = self._get_compare_data()
            data['status'] = 'limit_exceeded'
            data['message'] = 'Bạn chỉ có thể so sánh tối đa 3 sản phẩm.'
            return data

        curr_ids.append(p_id)
        self._set_compare_product_ids(curr_ids)
        data = self._get_compare_data()
        data['status'] = 'added'
        return data

    @http.route('/shop/compare/remove', type='jsonrpc', auth='public', website=True)
    def compare_remove(self, product_id, **kw):
        try:
            p_id = int(product_id)
        except (ValueError, TypeError):
            return self._get_compare_data()

        curr_ids = self._get_compare_product_ids()
        if p_id in curr_ids:
            curr_ids.remove(p_id)
            self._set_compare_product_ids(curr_ids)
        return self._get_compare_data()

    @http.route('/shop/compare/clear', type='jsonrpc', auth='public', website=True)
    def compare_clear(self, **kw):
        self._set_compare_product_ids([])
        return self._get_compare_data()

    @http.route('/compare', type='http', auth='public', website=True, sitemap=True)
    def compare_page(self, **kw):
        product_ids = self._get_compare_product_ids()
        products = request.env['product.template'].sudo().browse(product_ids).filtered(
            lambda p: p.exists() and p.website_published
        )
        website = request.website
        products_prices = products._get_sales_prices(website) if hasattr(products, '_get_sales_prices') else {}

        # 1. Tính toán các dòng có sự khác biệt (Differences Highlight)
        diffs = {}
        if len(products) > 1:
            diffs['brand'] = len(set(p.beautymatch_brand or '' for p in products)) > 1
            diffs['price'] = len(set(products_prices.get(p.id, {}).get('price_reduce', p.list_price) for p in products)) > 1
            diffs['volume'] = len(set(p.beautymatch_volume or '' for p in products)) > 1
            diffs['skin_type'] = len(set(p.beautymatch_skin_type or '' for p in products)) > 1
            diffs['skin_concern'] = len(set(p.beautymatch_skin_concern or '' for p in products)) > 1
            diffs['key_ingredients'] = len(set(p.beautymatch_key_ingredients or '' for p in products)) > 1
            diffs['routine_step'] = len(set(p.beautymatch_routine_step or '' for p in products)) > 1
            diffs['usage_time'] = len(set(p.beautymatch_usage_time or '' for p in products)) > 1
            diffs['budget_level'] = len(set(p.beautymatch_budget_level or '' for p in products)) > 1

        # 2. Gợi ý 'Phù hợp hơn nếu bạn...' (Dựa trên BeautyMatch fields, không thiên vị hay tự nhận tốt nhất)
        fit_advices = {}
        for p in products:
            skin_type_dict = dict(p._fields['beautymatch_skin_type'].selection) if 'beautymatch_skin_type' in p._fields else {}
            concern_dict = dict(p._fields['beautymatch_skin_concern'].selection) if 'beautymatch_skin_concern' in p._fields else {}
            step_dict = dict(p._fields['beautymatch_routine_step'].selection) if 'beautymatch_routine_step' in p._fields else {}
            time_dict = dict(p._fields['beautymatch_usage_time'].selection) if 'beautymatch_usage_time' in p._fields else {}

            st = skin_type_dict.get(p.beautymatch_skin_type, "mọi loại da")
            sc = concern_dict.get(p.beautymatch_skin_concern, "chăm sóc da hàng ngày")
            rs = step_dict.get(p.beautymatch_routine_step, "chu trình chăm sóc")
            ut = time_dict.get(p.beautymatch_usage_time, "sáng và tối")

            fit_advices[p.id] = (
                f"Làn da của bạn thuộc nhóm {st.lower()}, đang gặp vấn đề {sc.lower()} "
                f"và cần một sản phẩm bước {rs.lower()} dùng vào buổi {ut.lower()}."
            )

        return request.render('beautymatch.page_compare', {
            'products': products,
            'diffs': diffs,
            'fit_advices': fit_advices,
            'get_product_prices': lambda p: products_prices.get(p.id, {'price_reduce': p.list_price}),
        })

    @http.route(['/shop/compare'], type='http', auth='public', website=True, sitemap=False)
    def shop_compare_redirect(self, **post):
        """Chuyển hướng toàn bộ yêu cầu so sánh từ Odoo native /shop/compare sang trang chuẩn BeautyMatch /compare.
        Nếu có tham số ?products=..., tự động chuyển đổi sang template_id và đưa vào session BeautyMatch.
        """
        raw_products = post.get('products', '')
        if raw_products:
            variant_ids = [int(i) for i in raw_products.split(',') if i.isdigit()]
            if variant_ids:
                variants = request.env['product.product'].sudo().browse(variant_ids).exists()
                tmpl_ids = list(dict.fromkeys(variants.mapped('product_tmpl_id.id')))
                curr_ids = self._get_compare_product_ids()
                for tid in tmpl_ids:
                    if tid not in curr_ids and len(curr_ids) < 3:
                        curr_ids.append(tid)
                self._set_compare_product_ids(curr_ids)
        return request.redirect('/compare')

    @http.route('/shop/category/sunscreen', type='http', auth='public', website=True)
    def redirect_sunscreen_category(self, **kw):
        """Điều hướng thông minh danh mục chống nắng mà không cần hard-code id"""
        categ = request.env.ref('beautymatch.public_category_sunscreen', raise_if_not_found=False)
        if categ:
            return request.redirect(f'/shop/category/{request.env["ir.http"]._slug(categ)}')
        return request.redirect('/shop')


class BeautyMatchWishlistController(http.Controller):
    """Xử lý yêu thích và bỏ yêu thích sản phẩm 2 chiều (Toggle Wishlist)"""

    @http.route('/shop/wishlist/toggle', type='jsonrpc', auth='public', website=True)
    def shop_wishlist_toggle(self, product_id=None, product_template_id=None, **kw):
        """Bật / Tắt yêu thích sản phẩm (Thêm nếu chưa có, Bỏ nếu đã có)"""
        product = None
        if product_id:
            product = request.env['product.product'].sudo().browse(int(product_id))
        elif product_template_id:
            tmpl = request.env['product.template'].sudo().browse(int(product_template_id))
            if tmpl.exists():
                var_id = tmpl._get_first_possible_variant_id()
                if var_id:
                    product = request.env['product.product'].sudo().browse(var_id)

        if not product or not product.exists():
            return {'error': 'Sản phẩm không tồn tại'}

        Wishlist = request.env['product.wishlist'].sudo()
        is_public = request.website.is_public_user()
        partner_id = False if is_public else request.env.user.partner_id.id

        current_wishes = Wishlist.current()
        # Tìm các wish khớp với product variant hoặc template
        existing_wishes = current_wishes.filtered(
            lambda w: w.product_id.id == product.id or (w.product_id.product_tmpl_id.id == product.product_tmpl_id.id)
        )

        if existing_wishes:
            # 1. ĐÃ CÓ TRONG WISHLIST -> BỎ YÊU THÍCH (Remove)
            for w in existing_wishes:
                if is_public:
                    wish_ids = request.session.get('wishlist_ids') or []
                    if w.id in wish_ids:
                        wish_ids = [wid for wid in wish_ids if wid != w.id]
                        request.session['wishlist_ids'] = wish_ids
                        request.session.touch()
                w.sudo().unlink()
            action = 'removed'
        else:
            # 2. CHƯA CÓ TRONG WISHLIST -> THÊM YÊU THÍCH (Add)
            price = product.list_price or 0.0
            try:
                combo_info = product._get_combination_info_variant()
                if combo_info and 'price' in combo_info:
                    price = combo_info['price']
            except Exception:
                pass

            pricelist = request.pricelist or request.website.sudo().pricelist_id
            pricelist_id = pricelist.id if pricelist else False
            currency_id = request.website.currency_id.id

            new_wish = Wishlist._add_to_wishlist(
                pricelist_id,
                currency_id,
                request.website.id,
                price,
                product.id,
                partner_id
            )
            if is_public and new_wish:
                curr_ids = list(request.session.get('wishlist_ids') or [])
                if new_wish.id not in curr_ids:
                    curr_ids.append(new_wish.id)
                request.session['wishlist_ids'] = curr_ids
                request.session.touch()
            action = 'added'

        total_count = len(Wishlist.current())
        return {
            'action': action,
            'count': total_count,
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_name': product.name,
        }



