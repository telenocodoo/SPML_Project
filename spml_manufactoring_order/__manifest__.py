# -*- coding: utf-8 -*-
{
    'name': "mrp production",
    'summary': """
        mrp production""",
    'description': """
        mrp production
    """,
    'author': "Magdy, helcon",
    'website': "http://www.yourcompany.com",
    'category': 'mrp',
    'version': '0.1',
    'depends': ['mrp', 'purchase'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/mrp_production.xml',
        'views/quality_control_test.xml',
    ],
}
