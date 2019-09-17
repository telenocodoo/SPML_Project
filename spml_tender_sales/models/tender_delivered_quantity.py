# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import UserError


class TenderDeliveredQuantity(models.Model):
    _name = "tender.delivered.quantity"
    _rec_name = 'sale_id'

    tender_sales_id = fields.Many2one("tender.sales.lines")
    invoice_id = fields.Many2one("account.invoice")
    sale_id = fields.Many2one("sale.order")
    product_id = fields.Many2one("product.product")
    quantity = fields.Float('ordered Quantity')
    total_qty = fields.Float(string="Total delivery", store=True, compute='get_total_qty')
    tender_delivered_ids = fields.One2many("tender.delivered.quantity.lines", "tender_delivered_id")

    # @api.constrains('quantity')
    @api.multi
    def write(self, vals):
        res = super(TenderDeliveredQuantity, self).write(vals)
        for record in self:
            if record.total_qty > record.quantity:
                raise UserError(_("Total Quantity must be less than delivered Quantity"))
        self.tender_sales_id.delivered_quantity = self.total_qty
        return res

    @api.depends('tender_delivered_ids')
    def get_total_qty(self):
        for record in self:
            record.total_qty = sum(line.quantity for line in record.tender_delivered_ids)


class TenderDeliveredQuantityLines(models.Model):
    _name = "tender.delivered.quantity.lines"

    tender_delivered_id = fields.Many2one("tender.delivered.quantity")
    quantity = fields.Float()
    date = fields.Datetime(default=fields.datetime.now())

    @api.multi
    def move_quantity_to_stock(self):
        stock_id = self.env['stock.picking'].search([('origin', '=', self.tender_delivered_id.sale_id.name)])
        if stock_id:
            for line in stock_id:
                for record in line.move_ids_without_package:
                    if record.product_id.id == self.tender_delivered_id.product_id.id:
                        record.quantity_done = self.quantity
                x = line.button_validate()
                return x
                # return {
                #     'type': 'ir.actions.act_window',
                #     'name': 'stock move',
                #     'res_model': 'stock.picking',
                #     'res_id': line.id,
                #     'view_type': 'form',
                #     'view_mode': 'form',
                #     'target': 'current',
                # }


    # @api.multi
    # def transfer_quantity_to_product(self):
    #     print("yes")
    #
    # @api.constrains('balance')
    # def constrains_balance(self):
    #     if self.balance < 0:
    #         raise UserError(_("Balance must be greater than 0"))
    #
    # @api.depends('ordered_quantity', 'delivered_quantity')
    # def compute_balance(self):
    #     self.balance = self.ordered_quantity - self.delivered_quantity
    #
    # @api.depends('balance')
    # def compute_tender_state(self):
    #     if self.balance <= 0:
    #         self.state = 'close'
    #     else:
    #         self.state = 'open'

