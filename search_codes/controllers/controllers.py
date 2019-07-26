# -*- coding: utf-8 -*-
from odoo import http

# class SearchCodes(http.Controller):
#     @http.route('/search_codes/search_codes/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/search_codes/search_codes/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('search_codes.listing', {
#             'root': '/search_codes/search_codes',
#             'objects': http.request.env['search_codes.search_codes'].search([]),
#         })

#     @http.route('/search_codes/search_codes/objects/<model("search_codes.search_codes"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('search_codes.object', {
#             'object': obj
#         })