# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2017 Alphasoft
#    (<http://www.alphasoft.co.id>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Cash & Bank Transfer',
    'version': '12.0.0.1.0',
    'sequence': 1,
    'summary': 'Example of a module by Alphasoft.',
    'author': "Alphasoft",
    'website': 'http://www.alphasoft.co.id',
    'images':  ['images/main_screenshot.png'],
    'license': 'AGPL-3',
    'category': 'Accounting',
    'description': 'Module based on Alphasoft',
    'depends': ['account', 'aos_base_account'],
    'data': [
            'data/account_data.xml',
            "security/account_security.xml",
            "views/account_transfer.xml",
     ],
    'demo': [],
    'test': [],
    'qweb': [],
    'css': [],
    'js': [],
    'price': 35.00,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
}
