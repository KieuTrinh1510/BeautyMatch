# -*- coding: utf-8 -*-
{
    'name': 'BeautyMatch',
    'version': '19.0.1.0.0',
    'summary': 'Personalized skincare e-commerce for BeautyMatch',
    'description': """
BeautyMatch - Nền tảng thương mại điện tử mỹ phẩm & chăm sóc da cá nhân hóa
============================================================================
Giải pháp hỗ trợ khách hàng trả lời 3 câu hỏi cốt lõi:
- "Nên mua gì?"
- "Vì sao sản phẩm phù hợp với làn da?"
- "Sản phẩm nằm ở bước nào trong quy trình (Routine)?"

Tính năng chính:
- Mở rộng thông tin sản phẩm: Loại da, Vấn đề da, Hoạt chất, Bước trong Routine, Thời điểm sử dụng, Lý do phù hợp.
- Điều hướng mua sắm theo vấn đề da (/theo-van-de-da).
- Bài trắc nghiệm ngắn Beauty Quiz gợi ý sản phẩm và routine chuẩn khoa học (/beauty-quiz).
- Trang cẩm nang hướng dẫn routine buổi sáng & buổi tối (/routine).
- Khám phá thương hiệu chuẩn nguồn gốc (/brands).
    """,
    'category': 'Website/eCommerce',
    'author': 'BeautyMatch Team',
    'website': 'https://beautymatch.vn',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'website',
        'website_sale',
        'website_sale_wishlist',
        'website_blog',
        'portal_rating',
        'sale',
        'stock',
        'sale_stock',
        'product',
        'website_sale_loyalty',
        'website_sale_stock',
        'delivery',
        'payment',
        'payment_custom',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/website_templates.xml',
        'views/shop_and_product_views.xml',
        'views/website_menu.xml',
        'views/order_and_portal_templates.xml',
        'views/header_and_footer_templates.xml',
        'views/trust_and_support_templates.xml',
        'views/blog_templates.xml',
        'views/compare_templates.xml',
        'data/product_categories.xml',
        'data/beautymatch_product_attributes.xml',
        'data/beautymatch_products.xml',
        'data/beautymatch_pricelist.xml',
        'data/beautymatch_inventory.xml',
        'data/beautymatch_coupon.xml',
        'data/beautymatch_shipping.xml',
        'data/beautymatch_payment.xml',
        'data/beautymatch_blog_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'beautymatch/static/src/scss/beautymatch.scss',
            'beautymatch/static/src/js/compare.js',
            'beautymatch/static/src/js/wishlist.js',
            'beautymatch/static/src/js/product_detail.js',
            'beautymatch/static/src/js/shop_filters.js',
            'beautymatch/static/src/js/header_dropdown.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
