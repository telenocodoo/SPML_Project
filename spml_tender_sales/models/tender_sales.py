# -*- coding: utf-8 -*-

# from odoo import models, fields, api, _
# from odoo.exceptions import UserError


from odoo import api, fields, models, _, SUPERUSER_ID
# from odoo.osv import expression
# from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
# from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES



class TenderSalesDelivery(models.Model):
    _inherit ='stock.picking'

    def add_done_qty(self,line_ids,pid,qty):
        for rec in line_ids:
            print(rec.tender_id, rec.product_id, rec.delivered_quantity, rec.balance)
            if rec.product_id ==pid :
                rec.delivered_quantity += qty
    @api.multi
    def button_validate(self):
        stock_sale_id = self.sale_id.id
        tender_obj = self.env['tender.sales'].search([('sale_id', '=', stock_sale_id)])
        tender_line_ids = self.env['tender.sales.lines'].search([('tender_id', '=', tender_obj.id)])

        # print(stock_sale_id)

        #
        self.ensure_one()
        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some items to move.'))
        # else :


        # If no lots when needed, raise error
        picking_type = self.picking_type_id
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
                                 self.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
        no_reserved_quantities = all(
            float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in
            self.move_line_ids)
        if no_reserved_quantities and no_quantities_done:
            raise UserError(_(
                'You cannot validate a transfer if no quantites are reserved nor done. To force the transfer, switch in edit more and encode the done quantities.'))

        if picking_type.use_create_lots or picking_type.use_existing_lots:
            lines_to_check = self.move_line_ids
            if not no_quantities_done:
                lines_to_check = lines_to_check.filtered(
                    lambda line: float_compare(line.qty_done, 0,
                                               precision_rounding=line.product_uom_id.rounding)
                )

            for line in lines_to_check:
                product = line.product_id
                if product and product.tracking != 'none':
                    if not line.lot_name and not line.lot_id:
                        raise UserError(
                            _('You need to supply a Lot/Serial number for product %s.') % product.display_name)

        if no_quantities_done:
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
            view = self.env.ref('stock.view_overprocessed_transfer')
            wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.overprocessed.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        # Check backorder should check for other barcodes
        if self._check_backorder():
            for rec in self.move_line_ids:
                print(rec.qty_done, rec.product_id, rec.move_id.name, rec.move_id.product_uom_qty)
                self.add_done_qty(tender_line_ids, rec.product_id, rec.qty_done)
                # print(rec.qty_done, rec.product_id, rec.move_id.name, rec.move_id.product_uom_qty)

            print("hi... Validate haytham")
            return self.action_generate_backorder_wizard()
        self.action_done()
        return

#
# for rec in self.move_line_ids:
#     print(rec.qty_done, rec.product_id, rec.move_id.name, rec.move_id.product_uom_qty)
#     self.add_done_qty(tender_line_ids, rec.product_id, rec.qty_done)
#     print(rec.qty_done, rec.product_id, rec.move_id.name, rec.move_id.product_uom_qty)
#
# print("hi... Validate haytham")

class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_tender = fields.Boolean()
    period = fields.Selection(selection=[('weekly', 'weekly'), ('monthly', 'monthly'), ])
    tender_id = fields.Many2one("tender.sales")

    #This will over ride delivery button haytham
    @api.multi
    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids')
        print("hi ... haytham")
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = {} if default is None else default.copy()
        default.update({
            'is_tender': False
        })
        return super(SaleOrder, self).copy(default=default)

    @api.multi
    def tender_sales_action(self):
        tender_id = self.env['tender.sales']
        tender_line_id = self.env['tender.sales.lines']
        invoice_id = self.env['account.invoice'].search([('origin', '=', self.name)], limit=1)

        for record in self:
            tender_obj = tender_id.create({
                'sale_id': self.id,
                'period': self.period,
                'invoice_id': invoice_id.id,
            })
            for line in record.order_line:
                tender_line_id.create({
                    'tender_id': tender_obj.id,
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'cost': line.price_unit,
                    'tax_ids': [(6, 0, line.tax_id.ids)],
                    'total': line.price_subtotal,
                    # 'ordered_quantity': line.product_uom_qty,
                })
            record.is_tender = True
            self.tender_id = tender_obj.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tender Sales',
                'res_model': 'tender.sales',
                'res_id': tender_obj.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
            }


class AccountTAx(models.Model):
    _inherit = "account.tax"

    tender_id = fields.Many2one("tender.sales.lines")


class TenderWizardLines(models.TransientModel):
    _name = "tender.sales.wizard.lines"

    tender_wiz_id = fields.Many2one('tender.sales.wizard')
    line_id = fields.Many2one('tender.sales.lines')
    product1_id = fields.Many2one("product.product")
    quantity1 = fields.Float()
    cost1 = fields.Float()
    total1 = fields.Float()
    product2_id = fields.Many2one("product.product")
    quantity2 = fields.Float()
    cost2 = fields.Float()
    total2 = fields.Float()
    number = fields.Integer()


class TenderWizard(models.TransientModel):
    _name = "tender.sales.wizard"

    tender_id = fields.Many2one("tender.sales")
    tender_ids = fields.One2many("tender.sales.wizard.lines", "tender_wiz_id")
    product1_id = fields.Many2one("product.product")
    quantity1 = fields.Float()
    cost1 = fields.Float()
    total1 = fields.Float()
    note1 = fields.Char()
    line_id1 = fields.Many2one('tender.sales.lines')
    product2_id = fields.Many2one("product.product")
    quantity2 = fields.Float()
    cost2 = fields.Float()
    total2 = fields.Float()
    note2 = fields.Char()
    line_id2 = fields.Many2one('tender.sales.lines')

    def _prepare_item(self, line):
        """prepare lines data"""
        return {
            'line_id': line.id,
            'product1_id': line.product_id.id,
            'quantity1': line.balance,
            'cost1': line.cost,
            'total1': line.total,
            'number': line.number,
        }

    @api.model
    def default_get(self, fields_list):
        """get default lines"""
        res = super(TenderWizard, self).default_get(fields_list)
        request_line_obj = self.env['tender.sales']
        request_line_ids = self.env.context.get('active_ids', False)
        active_model = self.env.context.get('active_model', False)
        if not request_line_ids:
            return res
        assert active_model == 'tender.sales', \
            'Bad context propagation'
        items = []
        request_lines = request_line_obj.browse(request_line_ids[0])
        for record in request_lines:
            for line in record.tender_ids:
                if line.is_move:
                    items.append([0, 0, self._prepare_item(line)])
        res['tender_ids'] = items
        return res

    @api.multi
    def compute_product_quantity(self):
        quantity1 = 0
        total1 = 0
        total2 = 0
        tot2 = 0
        balance = 0
        balance2 = 0
        remain1 = 0
        remain2 = 0
        current_qty = 0
        for record in self:
            current_qty = self.quantity2
            quantity1 = int(record.total2 / record.cost1)
            total1 = quantity1 * record.cost1
            total2 = record.total2 - total1
            balance = int(total2 / record.cost2)
            tot2 = balance * record.cost2
            remain1 = total2 - tot2
            balance2 = current_qty - balance

        self.quantity1 = quantity1
        self.quantity2 = balance
        self.total1 = total1
        self.total2 = total2
        # self.remain1 = remain1
        # self.remain2 = remain2

        self.note2 += "and new quantity is " + str(balance) + "and remain" + str(remain1)
        self.note1 += "and we add " + str(quantity1)

        self.line_id1.write({
            'ordered_quantity': self.line_id1.ordered_quantity + self.quantity1,
            'note': self.note1,
        })
        # self.quantity2
        self.line_id2.write({
            'ordered_quantity': self.line_id2.ordered_quantity-balance2,
            'note': self.note2,
        })

    @api.multi
    def move_product_quantity(self):
        create = False
        for rec in self:
            for line in rec.tender_ids:
                if line.number == 1:
                    self.product1_id =line.product1_id.id
                    self.quantity1 =line.quantity1
                    self.cost1 =line.cost1
                    self.total1 =line.total1
                    self.note1 = "old balance is " + str(line.quantity1)
                    self.line_id1 =line.line_id
                else:
                    self.product2_id =line.product1_id.id
                    self.quantity2 =line.quantity1
                    self.cost2 =line.cost1
                    self.total2 =line.total1
                    self.note2 = "old balance is " + str(line.quantity1)
                    self.line_id2 =line.line_id
                create = True
        # context = self.env.context
        # act_ids = context.get('active_ids', [])
        # print("dddddddd, ", act_ids)


class TenderSales(models.Model):
    _name = "tender.sales"
    _rec_name = 'sale_id'

    sale_id = fields.Many2one("sale.order")
    invoice_id = fields.Many2one("account.invoice")
    tender_ids = fields.One2many("tender.sales.lines", "tender_id")
    period = fields.Selection(selection=[('weekly', 'weekly'), ('monthly', 'monthly'), ])


    # This will over ride delivery button haytham
    @api.multi
    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids')
        print("hi ... haytham sales tender")
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    @api.multi
    def transfer_quantity_to_product(self):
        print("yes")
        lst = []
        for record in self:
            for line in record.tender_ids:
                if line.is_move:
                    lst.append(line)
        if len(lst) != 2:
            raise UserError(_("The selected lines Must be two lines"))

        return {
                'type': 'ir.actions.act_window',
                'name': 'Tender Sales wizard',
                'res_model': 'tender.sales.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'context': {'default_tender_id': self.id},
                'target': 'current',
            }


class TenderSalesLines(models.Model):
    _name = "tender.sales.lines"

    tender_id = fields.Many2one("tender.sales")
    product_id = fields.Many2one("product.product")
    quantity = fields.Float(string="ordered Qty")
    sequence = fields.Integer()
    number = fields.Integer()
    cost = fields.Float()
    total = fields.Float(compute="compute_total_price")
    tax_ids = fields.Many2many("account.tax", "tender_id")
    ordered_quantity = fields.Float(string="Transfer Qty")
    delivered_quantity = fields.Float()
    balance = fields.Float(store=True, compute='compute_balance')
    state = fields.Selection(selection=[('close', 'close'), ('open', 'open')], compute='compute_tender_state')
    note = fields.Char()
    is_move = fields.Boolean()

    @api.multi
    def transfer_product_quantity(self):
        tender_delivery_id = self.env['tender.delivered.quantity']
        tender_search_id = tender_delivery_id.search([('tender_sales_id', '=', self.id)])
        if tender_search_id:
            if tender_search_id.quantity < self.quantity + self.ordered_quantity:
                tender_search_id.quantity = self.quantity + self.ordered_quantity
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tender Delivered Quantity',
                'res_model': 'tender.delivered.quantity',
                'res_id': tender_search_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
            }

        else:
            tender_id = tender_delivery_id.create({
                'tender_sales_id': self.id,
                'product_id': self.product_id.id,
                'invoice_id': self.tender_id.invoice_id.id,
                'sale_id': self.tender_id.sale_id.id,
                'quantity': self.quantity + self.ordered_quantity,
            })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tender Delivered Quantity',
                'res_model': 'tender.delivered.quantity',
                'res_id': tender_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
            }

    @api.constrains('balance')
    def constrains_balance(self):
        for record in self:
            if record.balance < 0:
                raise UserError(_("Balance must be greater than 0"))

    @api.depends('ordered_quantity', 'delivered_quantity')
    def compute_balance(self):
        for record in self:
            record.balance = (record.ordered_quantity + record.quantity) - record.delivered_quantity

    @api.depends('balance', 'cost')
    def compute_total_price(self):
        for record in self:
            record.total = record.balance * record.cost

    @api.depends('balance')
    def compute_tender_state(self):
        for record in self:
            if record.balance <= 0:
                record.state = 'close'
            else:
                record.state = 'open'
