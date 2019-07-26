# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_status = fields.Char("Delivery Status", compute="_compute_delivery_status", store=True)

    @api.multi
    @api.depends('picking_ids.state')
    def _compute_delivery_status(self):

        for records in self:
            if records.picking_ids:
                states = []
                for picking in records.picking_ids:
                    states.append(picking.state)
                states = set(states)
                if 'draft' in states:
                    records.delivery_status = 'Draft'
                elif 'confirmed' in states:
                    records.delivery_status = 'Waiting'
                elif 'assigned' in states:
                    records.delivery_status = 'Ready'
                elif 'done' in states:
                    records.delivery_status = 'Done'