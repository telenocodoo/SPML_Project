# -*- coding: utf-8 -*-
from odoo import http

# class Autocustomer(http.Controller):
#     @http.route('/autocustomer/autocustomer/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/autocustomer/autocustomer/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('autocustomer.listing', {
#             'root': '/autocustomer/autocustomer',
#             'objects': http.request.env['autocustomer.autocustomer'].search([]),
#         })

#     @http.route('/autocustomer/autocustomer/objects/<model("autocustomer.autocustomer"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('autocustomer.object', {
#             'object': obj
#         })