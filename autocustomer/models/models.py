# -*- coding: utf-8 -*-

from odoo import models, fields, api
# from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _name = _inherit
    code=fields.Char(string="Customer Code")

    @api.model
    def create(self, vals):
        if 'customer' in vals and vals['customer']:
            vals['code'] = self.env['ir.sequence'].get('customer.number')
            # vals['code'] =  vals['ref']


        return super(ResPartner, self).create(vals)

# class autocustomer(models.Model):
#     _name = 'autocustomer.autocustomer'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100