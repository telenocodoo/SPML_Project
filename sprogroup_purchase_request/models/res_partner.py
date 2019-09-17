from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_attach_ids = fields.One2many(comodel_name="res.partner.attach", inverse_name="partner_id")
    is_approved = fields.Selection(selection=[('required', 'Required'),
                                              ('not_required', 'Not Required'),
                                              ('temporary_approved', 'Temporary Approved'),
                                              ], string='Vendor state', default='not_required')


class ResPartnerAttach(models.Model):
    _name = 'res.partner.attach'

    partner_id = fields.Many2one('res.partner')
    name = fields.Char()
    attach_id = fields.Binary(string="Attachment")

