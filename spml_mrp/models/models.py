# # -*- coding: utf-8 -*-
#
from odoo import models, fields, api ,_
# from odoo.addons import decimal_precision as dp
# from odoo.exceptions import UserError, ValidationError
# from odoo.tools import float_round

from itertools import groupby, filterfalse


#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#digits=(16,4)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    standard_price = fields.Float(
        'Cost', compute='_compute_standard_price',
        inverse='_set_standard_price', search='_search_standard_price',
        digits= (16,4) , groups="base.group_user",
        help = "Cost used for stock valuation in standard price and as a first price to set in average/FIFO.")

class MrpBom(models.Model):

     _inherit =  'mrp.bom'

     comp_total = fields.Float(string="Component Total" ,digits=(16,4),compute="_calc_comp_total")
     bom_extra_line_ids = fields.One2many('mrp.bom.extra', 'bom_id', 'BoM Extra' )
     Extra_total = fields.Float(string="Extra Total",compute="_calc_comp_total" )
     final_total_cost=fields.Float(string="Final  Total Cost",digits=(16,5), compute="_calc_comp_total")
     final_total_cost_after_waste=fields.Float(string="Final Total Cost",digits=(16,5), compute="_calc_comp_total_waste")
     markup_percentage=fields.Float(string="%markup",digits=(16,5))
     may_sell_by = fields.Float(string="May Sell by ", digits=(16, 5),compute="_calc_markup" )

     divid=fields.Float(string="Quantity divid",digits=(16,0),required=True)
     comp_per_divid =fields.Float(string="Per cost",digits=(16,4) ,compute="_calc_per_divid")
     fill_volume =fields.Float(string="Fill Volume",required=True)
     comp_total_per_fill=fields.Float(string="Total Volume cost",digits=(16,5) ,compute="_calc_volume_cost")
     percent_age_waste=fields.Float(string="%Age waste",digits=(16,2),required=True)
     cost_of_waste =fields.Float(string="Per cost",digits=(16,4) ,compute="_calc_cost_waste")
     current_sell_price=fields.Float(string="current selling price",digits=(16,4))
     Veriable_Overhead=fields.Float(string=" Veriable Overhead ",digits=(16,4),default=.08 )
     Direct_Labour=fields.Float(string="Direct Labour",digits=(16,4),default=.12 )

     @api.depends('markup_percentage')
     def _calc_markup(self):
         self.may_sell_by = 0.0
         if self.markup_percentage and self.markup_percentage !=0 and self.final_total_cost_after_waste:
             self.may_sell_by = self.final_total_cost_after_waste+(self.final_total_cost_after_waste * (self.markup_percentage / 100))
     # @api.depends('percent_age_waste')
     # def _calc_cost_waste(self):
     #     self.cost_of_waste = 0.0
     #     if self.final_total_cost:
     #         self.final_total_cost_after_waste = self.final_total_cost +self.cost_of_waste
     #         # print("final cost ",self.final_total_cost,self.cost_of_waste)
     #         # self.final_total_cost +=self.cost_of_waste
     #         # print("final cost ",self.final_total_cost,self.cost_of_waste)

     @api.depends('percent_age_waste')
     def _calc_cost_waste(self):
         self.cost_of_waste=0.0
         if self.final_total_cost :
             self.cost_of_waste=self.final_total_cost * (self.percent_age_waste/100)
             # print("final cost ",self.final_total_cost,self.cost_of_waste)
             # self.final_total_cost +=self.cost_of_waste
             # print("final cost ",self.final_total_cost,self.cost_of_waste)


     @api.depends('fill_volume')
     def _calc_volume_cost(self):
         print(self.comp_per_divid , self.comp_total , self.fill_volume , self.fill_volume )
         if self.comp_per_divid and self.comp_total and self.fill_volume and self.fill_volume !=0:

             self.comp_total_per_fill = self.comp_per_divid * self.fill_volume
             print(self.comp_total_per_fill)
         else:
             self.comp_total_per_fill = 0.0

     @api.depends('divid')
     def _calc_per_divid(self):
         print(self.comp_per_divid , self.comp_total , self.divid )

         if  self.comp_total and self.divid !=0:
            self.comp_per_divid=self.comp_total/self.divid
         else:
             self.comp_per_divid =0.0

     @api.multi
     def _calc_comp_total_waste(self):
         product_cost_id = self.env['product.product'].search([('product_tmpl_id', '=',self.product_tmpl_id.id)],limit=1)

         # print(self.product_tmpl_id.name)
         self.final_total_cost_after_waste = self.final_total_cost + self.cost_of_waste+self.Veriable_Overhead+self.Direct_Labour
         product_cost_id.standard_price=self.final_total_cost_after_waste
         # if product_cost_id :
         #    product_cost_id.standard_price=self.final_total_cost_after_waste
         #    print( "hi... cost ",product_cost_id.standard_price)
         #    p = self.env['product.product'].browse(product_cost_id.id)
         #    # self.env['post.coder'].write(code_check, {'street': self.buyer_address_1})
         #
         #        # print(product_cost_id.standard_price)
         #    p.write({'standard_price': product_cost_id.standard_price})
         #    print(p)

     @api.model
     def create(self, vals):
         res = super(MrpBom, self).create(vals)
         res.write({'code': res.code})
         return res

     @api.multi
     def write(self, vals):
         res = super(MrpBom, self).write(vals)
         for bom in self:

             bom.product_tmpl_id.standard_price = self.final_total_cost_after_waste
         return res

     @api.multi
     def _calc_comp_total(self):
         self.comp_total=0.0
         self.Extra_total=0.0
         self.final_total_cost=0.0
         print(self.comp_total)
         if self.bom_line_ids :
             for rec in  self.bom_line_ids:
                 self.comp_total +=rec.Total
         print(self.comp_total)
         if self.bom_extra_line_ids:
              for rec in self.bom_extra_line_ids:

                  # print (rec.total)
                 self.Extra_total += rec.total
         self.final_total_cost = self.Extra_total + self.comp_total_per_fill #+self.cost_of_waste



#
#     @api.multi
#     def _compute_bom_cost(self):
#         for bom in self:
#             totale_cost = 0.0
#             # for bom_line in bom.bom_line_ids:
#             #     if bom_line.related_bom_ids:
#             #         for sub_bom in bom_line.related_bom_ids:
#             #             if bom.type in [sub_bom.type, 'phantom']:
#             #                 if sub_bom:
#             #                     totale_cost = totale_cost + sub_bom.standard_price * bom_line.product_qty
#             #                     break
#             #     else:
#             #         totale_cost = totale_cost + bom_line.product_id.standard_price * bom_line.product_qty
#             # bom.standard_price = totale_cost
#
#     standard_price = fields.Float(compute=_compute_bom_cost)
#
#

# class MRPBom_in (models.Model):
#     _inherit ='mrp.bom'
#     bom_line_ids = fields.One2many('mrp.bom.extra', 'bom_id', 'BoM Extra', copy=True)
#

class MRPBomExtra (models.Model):
    _name='mrp.bom.extra'

    name=fields.Char(string="Name")
    quantity=fields.Float(string="Quantity",default=1.0)
    actual_cost=fields.Float(string="Actual Cost",digits=(16, 4))
    total=fields.Float("Total",compute="_calc_total_extra" , digits=(16, 4))
    # extra_total =fields.Float("Extra Total",digits=(16, 3))



    bom_id = fields.Many2one(
        'mrp.bom', 'Parent BoM')
    # product_id = fields.Many2one(
    #     'product.product', 'Component', required=True)
    # product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id',
    #                                   readonly=False)
    # sequence = fields.Integer(
    #     'Sequence', default=1,
    #     help="Gives the sequence order when displaying.")


    @api.depends('actual_cost', 'quantity')
    def _calc_total_extra(self):
        extra_total = 0.0
        if self:
            for rec in self:

                extra_total += rec.quantity * rec.actual_cost
                rec.total = rec.quantity * rec.actual_cost


        # print(self.extra_total)

class product_price(models.Model):
    _inherit="product.product"

    standard_price = fields.Float(
        'Cost', company_dependent=True,
        digits=(16,4),
        groups="base.group_user",
        help="Cost used for stock valuation in standard price and as a first price to set in average/fifo. "
             "Also used as a base price for pricelists. "
             "Expressed in the default unit of measure of the product.")

class MrpBomLine(models.Model):
#
    _inherit = 'mrp.bom.line'
    product_cost=fields.Float(related='product_id.standard_price',store=True,digits=(16, 4))
    actual_cost=fields.Float(string="Actual Cost",default=0,digits=(16, 4))

    Total=fields.Float(string="Total",compute="_calc_total",digits=(16, 4))


    @api.depends ('product_id','actual_cost','product_qty')
    def _calc_total(self):
        self.comp_total=0.0
        if self:
            for rec in self:
                    if  rec.actual_cost ==0 :
                        rec.actual_cost = rec.product_cost

                    self.comp_total += rec.product_qty * rec.actual_cost
                    rec.Total = rec.product_qty * rec.actual_cost
        print(self.comp_total)

#     @api.depends ('product_id')
#     def _calc_total(self):
#
#         if self:
#             for rec in self:
#                 if  rec.actual_cost !=  rec.product_cost and  rec.actual_cost !=0:
#                     rec.actual_cost= rec.product_cost
#
# #
#     @api.multi
#     def _compute_bom_cost(self):
#         for bom_line in self:
#             totale_cost = 0.0
#         #     cost_found = False
#         #     if bom_line.related_bom_ids:
#         #         for sub_bom in bom_line.related_bom_ids:
#         #             if bom_line.bom_id.type == sub_bom.type:
#         #                 if sub_bom:
#         #                     bom_line.standard_price = totale_cost + sub_bom.standard_price
#         #                     cost_found = True
#         #                     break
#         #     if not cost_found:
#         #         bom_line.standard_price = bom_line.product_id.standard_price
#
#     standard_price = fields.Float(compute=_compute_bom_cost)
