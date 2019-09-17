from odoo import api, fields, models, _
from odoo.exceptions import UserError

class QualityPurchase(models.Model):
    _name = 'quality.purchase'

    quality_purchase_ids = fields.One2many(comodel_name="quality.purchase.line", inverse_name="quality_purchase_id")
    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
    picking_type_id = fields.Many2one('stock.picking.type')
    scheduled_date = fields.Datetime(string="scheduled date")
    state = fields.Selection(selection=[('draft', 'draft'), ('pass', 'pass'), ('fail', 'fail')], default='draft')

    @api.multi
    def pass_quality_purchase(self):
        stock_id = self.env['stock.picking']
        stock_obj = stock_id.search([('name', '=', self.name)])
        if stock_obj:
            for stock in stock_obj:
                stock.quality_state = 'pass'
        self.state = 'pass'


    @api.multi
    def fail_quality_purchase(self):
        stock_id = self.env['stock.picking']
        stock_obj = stock_id.search([('name', '=', self.name)])
        if stock_obj:
            for stock in stock_obj:
                stock.quality_state = 'fail'
        self.state = 'fail'


class QualityPurchaseLine(models.Model):
    _name = 'quality.purchase.line'

    quality_purchase_id = fields.Many2one('quality.purchase')
    product_id = fields.Many2one('product.product')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    quality_state = fields.Selection(selection=[('pass', 'pass'), ('fail', 'fail')])
    quality_id = fields.Many2one('quality.purchase')

    @api.multi
    def button_validate(self):
        if self.quality_state != 'pass':
            raise UserError(_("You need approval from QC"))
        else:
            return super(StockPicking, self).button_validate()
        
    @api.multi
    def make_quality_purchase(self):
        quality_purchase_id = self.env['quality.purchase']
        quality_line_id = self.env['quality.purchase.line']
        qc_id = quality_purchase_id.search([('name', '=', self.name)])
        if qc_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'quality purchase',
                'res_model': 'quality.purchase',
                'res_id': qc_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current'
            }
        else:
            quality_obj = quality_purchase_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id,
                'picking_type_id': self.picking_type_id.id,
                'scheduled_date': self.scheduled_date,
            })
            for line in self.move_ids_without_package:
                quality_line_id.create({
                    'quality_purchase_id': quality_obj.id,
                    'product_id': line.product_id.id,
                })
            self.quality_id = quality_obj.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'quality purchase',
                'res_model': 'quality.purchase',
                'res_id': quality_obj.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current'
            }
