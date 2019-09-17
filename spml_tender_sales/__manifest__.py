# -*- coding: utf-8 -*-
{
    'name': "Tender Sales",
    'summary': """Tender Sales""",
    'description': """Tender Sales""",
    'author': "Magdy, helcon",
    'website': "http://www.yourcompany.com",
    'category': 'sale',
    'version': '0.1',
    'depends': ['sale','stock',],
    'data': [
        # 'security/security.xml',
        'security/ir.model.access.csv',
        'views/tender_sales.xml',
        'views/tender_delivered_quantity.xml',
    ],
}
