# -*- coding: utf-8 -*-
from odoo import http

# class SpmlBatch(http.Controller):
#     @http.route('/spml_batch/spml_batch/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/spml_batch/spml_batch/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('spml_batch.listing', {
#             'root': '/spml_batch/spml_batch',
#             'objects': http.request.env['spml_batch.spml_batch'].search([]),
#         })

#     @http.route('/spml_batch/spml_batch/objects/<model("spml_batch.spml_batch"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('spml_batch.object', {
#             'object': obj
#         })