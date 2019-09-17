# -*- coding: utf-8 -*-
from odoo import http

# class SpmlProductSearch(http.Controller):
#     @http.route('/spml__product_search/spml__product_search/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/spml__product_search/spml__product_search/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('spml__product_search.listing', {
#             'root': '/spml__product_search/spml__product_search',
#             'objects': http.request.env['spml__product_search.spml__product_search'].search([]),
#         })

#     @http.route('/spml__product_search/spml__product_search/objects/<model("spml__product_search.spml__product_search"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('spml__product_search.object', {
#             'object': obj
#         })