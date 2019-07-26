# -*- coding: utf-8 -*-
from odoo import http

# class SpmlMrp(http.Controller):
#     @http.route('/spml_mrp/spml_mrp/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/spml_mrp/spml_mrp/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('spml_mrp.listing', {
#             'root': '/spml_mrp/spml_mrp',
#             'objects': http.request.env['spml_mrp.spml_mrp'].search([]),
#         })

#     @http.route('/spml_mrp/spml_mrp/objects/<model("spml_mrp.spml_mrp"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('spml_mrp.object', {
#             'object': obj
#         })