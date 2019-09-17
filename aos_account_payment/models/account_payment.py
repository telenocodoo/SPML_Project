# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import openerp.addons.decimal_precision as dp

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}
# Since invoice amounts are unsigned, this is how we know if money comes in or goes out
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': 1,
    'in_invoice': -1,
    'out_refund': -1,
}

class account_payment(models.Model):
    _name = "account.payment"
    _inherit = ['account.payment', 'mail.thread']
    
    def _set_currency_rate(self):
        for payment in self:
            if payment.is_force_curr:
                company_currency = payment.journal_id.company_id.currency_id
                payment_currency = payment.currency_id or company_currency
                payment.force_rate = payment_currency.with_context(date=payment.payment_date).compute(1.0, company_currency, round=False)
                payment.company_currency_id = company_currency.id
            else:
                payment.force_rate = 0.0
        
    def _prepare_account_move_line(self, line):
        data = {
            'move_line_id': line.id,
            'date':line.date,
            'date_due':line.date_maturity,
            'type': line.debit and 'dr' or 'cr',
            'invoice_id': line.invoice_id.id,
            'name': line.invoice_id.name or line.name or '/',
        }
        company_currency = self.journal_id.company_id.currency_id
        payment_currency = self.currency_id or company_currency
        if line.currency_id and payment_currency==line.currency_id:
            data['amount_total'] = abs(line.amount_currency)
            data['residual'] = abs(line.amount_residual_currency)
            data['amount_to_pay'] = 0.0#abs(line.amount_residual_currency)
        else:
            #always use the amount booked in the company currency as the basis of the conversion into the voucher currency
            data['amount_total'] = company_currency.compute(line.credit or line.debit or 0.0, payment_currency, round=False)#currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.credit or move_line.debit or 0.0, context=ctx)
            data['residual'] = company_currency.compute(abs(line.amount_residual), payment_currency, round=False)#currency_pool.compute(cr, uid, company_currency, voucher_currency, abs(move_line.amount_residual), context=ctx)
            data['amount_to_pay'] = 0.0#company_currency.compute(abs(line.amount_residual), payment_currency, round=False)#currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.credit or move_line.debit or 0.0, context=ctx)
        return data
    
    @api.multi
    def _set_outstanding_lines(self, partner_id, account_id, currency_id, journal_id, payment_date):
        for payment in self:
            if payment.register_ids:
                payment.register_ids.unlink()
            account_type = None
            if self.payment_type == 'outbound':
                account_type = 'payable'
            else:
                account_type = 'receivable'
            new_lines = self.env['account.payment.line']
            #SEARCH FOR MOVE LINE; RECEIVABLE/PAYABLE AND NOT FULL RECONCILED
            if account_id:
                move_lines = self.env['account.move.line'].search([('account_id','=',account_id.id),('account_id.internal_type','=',account_type),('partner_id','=',partner_id.id),('reconciled','=',False)])
            else:
                move_lines = self.env['account.move.line'].search([('account_id.internal_type','=',account_type),('partner_id','=',partner_id.id),('reconciled','=',False)])
            #print "==_set_outstanding_lines===",move_lines
            for line in move_lines:
                data = payment._prepare_account_move_line(line)
                new_line = new_lines.new(data)
                new_lines += new_line
            payment.register_ids += new_lines
            #'invoice_ids': [(4, inv.id, None) for inv in self._get_invoices()]
            
    @api.one
    @api.depends('payment_type', 'amount', 'amount_charges', 'other_lines')
    def _compute_price(self):
        total_other = 0.0
        for oth in self.other_lines:
            total_other += oth.amount
        if self.advance_type == 'cash':
            self.amount_subtotal = self.amount - self.amount_charges - total_other
        else:
            self.amount_subtotal = self.amount + self.amount_charges + total_other
            
    @api.multi
    def _set_invoice_ids(self):
        for payment in self:
            payment.invoice_ids = [(4, reg.invoice_id.id, None) for reg in payment.register_ids]
            
#     advance_type = fields.Selection([('invoice', 'Reconcile to Invoice'), 
#                                      ('advance', 'Down Payment'), 
#                                      ('advance_emp', 'Employee Advance'),
#                                      ('receivable_emp','Employee Receivable')], default='invoice', string='Type')
    #state = fields.Selection(selection_add=[('confirm', 'Confirm')])
    #('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled')
    state = fields.Selection(selection_add=[('confirm', 'Confirm')])
    register_date = fields.Date(string='Register Date', required=False, copy=False)
    payment_date = fields.Date(string='Posted Date', required=False, copy=False)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency')
#     is_force_curr = fields.Boolean('Kurs Nego')
#     force_rate = fields.Monetary('Kurs Nego Amount')
    name = fields.Char(readonly=True, copy=False, default="Number")
    customer_account_id = fields.Many2one('account.account', string='Customer Account', domain=[('reconcile','=',True)])
    supplier_account_id = fields.Many2one('account.account', string='Supplier Account', domain=[('reconcile','=',True)])
    communication = fields.Char(string='Ref#')
    register_ids = fields.One2many('account.payment.line', 'payment_id', copy=False, string='Register Invoice')
    #================make charge transfer=======================================
#     amount_charges = fields.Monetary(string='Amount Adm', required=False)
#     charge_account_id = fields.Many2one('account.account', string='Account Adm', domain=[('user_type_id.name','=','601.00 Expenses')])
    residual_account_id = fields.Many2one('account.account', string='Residual Account', domain=[('deprecated','=',False)])
    #===========================================================================
    other_lines = fields.One2many('account.payment.other', 'payment_id', string='Payment Lines')
    #===========================================================================
#     payment_adm = fields.Selection([
#             ('cash','Cash'),
#             ('free_transfer','Non Payment Administration Transfer'),
#             ('transfer','Transfer'),
#             #('check','Check/Giro'),
#             #('letter','Letter Credit'),
#             ('cc','Credit Card'),
#             ('dc','Debit Card'),
#             ],string='Payment Adm')
#     card_number = fields.Char('Card Number', size=128, required=False)
#     card_type = fields.Selection([
#             ('visa','Visa'),
#             ('master','Master'),
#             ('bca','BCA Card'),
#             ('citi','CITI Card'),
#             ('amex','AMEX'),
#             ], string='Card Type', size=128)
    notes = fields.Text('Notes')
    amount_subtotal = fields.Monetary(string='Amount Total',
        store=True, readonly=True, compute='_compute_price')
        
    
    @api.onchange('is_force_curr')
    def _onchange_is_force_curr(self):
        self._set_currency_rate()
        
#     @api.onchange('partner_id', 'customer_account_id', 'currency_id', 'journal_id', 'payment_date')
#     def _onchange_partner_id(self):
#         if self.partner_id and self.customer_account_id and self.currency_id and self.journal_id and self.payment_date:
#             self._set_currency_rate()
#             self._set_outstanding_lines(self.partner_id, self.customer_account_id, self.currency_id, self.journal_id, self.payment_date)
    
    @api.onchange('register_ids')
    def _onchange_register_ids(self):
        amount = amount_subtotal = 0.0
        for line in self.register_ids:
            #if line.action:
            amount += line.amount_to_pay
#         total_other = 0.0
#         for oth in self.other_lines:
#             total_other += oth.amount
#         if self.advance_type == 'cash':
#             amount_subtotal = amount - self.amount_charges - total_other
#         else:
#             amount_subtotal = amount + self.amount_charges + total_other
        self.amount = amount
#         self.amount_subtotal = amount_subtotal
        return
    
    @api.multi
    def button_outstanding(self):
        #print "==button_outstanding=="
        for payment in self:
            account_id = payment.customer_account_id or payment.supplier_account_id or False
            if payment.partner_id and payment.currency_id and payment.journal_id and payment.payment_date:
                payment._set_currency_rate()
                payment._set_outstanding_lines(payment.partner_id, account_id, payment.currency_id, payment.journal_id, payment.payment_date)
                payment._set_invoice_ids()
                #print "===payment==",payment.register_ids
                #payment.invoice_ids = [(4, reg.invoice_id.id, None) for reg in payment.register_ids()]
         
    @api.model
    def default_get(self, fields):
        rec = super(account_payment, self).default_get(fields)
        invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
        #print "===checkline_defaults===",checkline_defaults
        if invoice_defaults and len(invoice_defaults) == 1:
            invoice = invoice_defaults[0]
            #print "===default===",invoice['sale_id'],invoice['number']#,invoice['sale_id']['name'],invoice['number']
            if 'sale_id' in invoice:
                communication = invoice['sale_id'] and invoice['number'] + ':' + invoice['sale_id'][1]
            else:
                communication = invoice['number']
            rec['communication'] = communication
            rec['currency_id'] = invoice['currency_id'][0]
            rec['payment_type'] = invoice['type'] in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
            rec['partner_type'] = MAP_INVOICE_TYPE_PARTNER_TYPE[invoice['type']]
            rec['partner_id'] = invoice['partner_id'][0]
            rec['amount'] = invoice['residual']
        return rec
    
    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id', 'customer_account_id', 'supplier_account_id')
    def _compute_destination_account_id(self):
        if self.invoice_ids:
            self.destination_account_id = self.invoice_ids[0].account_id.id
        elif self.payment_type == 'transfer':
            if self.advance_type == 'advance_emp':
                self.destination_account_id = self.customer_account_id and self.customer_account_id.id
            else:
                if not self.company_id.transfer_account_id.id:
                    raise UserError(_('Transfer account not defined on the company.'))
                self.destination_account_id = self.company_id.transfer_account_id.id
        elif self.partner_id:
            if self.partner_type == 'customer':
                if self.advance_type == 'advance':
                    self.destination_account_id = self.customer_account_id and self.customer_account_id.id or self.partner_id.property_account_advance_receivable_id and self.partner_id.property_account_advance_receivable_id.id
                else:
                    self.destination_account_id = self.customer_account_id and self.customer_account_id.id or self.partner_id.property_account_receivable_id and self.partner_id.property_account_receivable_id.id
            elif self.partner_type == 'supplier':
                if self.advance_type == 'advance':
                    self.destination_account_id = self.supplier_account_id and self.supplier_account_id.id or self.partner_id.property_account_advance_payable_id and self.partner_id.property_account_advance_payable_id.id
                else:
                    self.destination_account_id = self.supplier_account_id and self.supplier_account_id.id or self.partner_id.property_account_payable_id and self.partner_id.property_account_payable_id.id
            else:
                if self.advance_type == 'advance_emp':
                    self.destination_account_id = self.destination_journal_id.default_credit_account_id.id
        elif not self.partner_id:
            if self.partner_type == 'customer':
                self.destination_account_id = self.customer_account_id.id
            else:
                self.destination_account_id = self.supplier_account_id.id
            
    @api.onchange('destination_journal_id')
    def _onchange_destination_journal(self):
        if self.destination_journal_id:
            self.destination_account_id = self.destination_journal_id.default_debit_account_id and self.destination_journal_id.default_debit_account_id.id or self.destination_journal_id.default_credit_account_id or self.destination_journal_id.default_debit_account_id.id or False               
    
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        res = super(account_payment, self)._onchange_payment_type()
        return res
    
    def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
        context = dict(self._context or {})
        if context.get('charge_counter_id') or context.get('charge_liquidity_id'):
            res = super(account_payment, self)._get_shared_move_line_vals(credit, debit, amount_currency, move_id, invoice_id)
            res['name'] = 'BIAYA ADMIN'
        else:
            res = super(account_payment, self)._get_shared_move_line_vals(debit, credit, amount_currency, move_id, invoice_id)
        res['partner_id'] = (self.payment_type in ('inbound', 'outbound') or self.advance_type == 'advance_emp') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False
        return res
    
    @api.multi
    def action_cancel(self):
        for rec in self:
#             for line in rec.register_ids:
#                 if line.statement_line_id and line.statement_id.state == 'confirm':
#                     raise UserError(_("Please set the bank statement to New before canceling."))
#                 line.statement_line_id.unlink()
            rec.state = 'draft'
    
#     @api.multi
#     def cancel(self):
#         res = super(account_payment, self).cancel()
#         for rec in self:
#             for line in rec.register_ids:
#                 if line.statement_line_id and line.statement_line_id.state == 'confirm':
#                     raise UserError(_("Please set the bank statement to New before canceling."))
#                 line.statement_line_id.unlink()
#         return res
            
    @api.multi
    def cancel_transfer(self):
        for rec in self:
            for move in rec.move_line_ids.mapped('move_id'):
                if rec.invoice_ids:
                    move.line_ids.remove_move_reconcile()
                move.button_cancel()
                move.unlink()
            rec.state = 'draft'
    
#     @api.multi
#     def confirm(self):
#         for rec in self:
#             rec.state = 'confirm'

            
    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            #CHANGE STATE CONFIRM WHICH CAN BE POSTED
            #if rec.state != 'draft':
            #    raise UserError(_("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
#             Statement = self.env['account.bank.statement']
#             StatementLine = self.env['account.bank.statement.line']
#             statement_id = Statement.search([('journal_id','=',rec.journal_id.id),
#                                              ('date','>=',rec.payment_date),
#                                              ('date','<=',rec.payment_date)], limit=1)
#             if not statement_id:
#                 statement_id = Statement.create({'journal_id': rec.journal_id.id, 'date': rec.payment_date})
            
            # Create the journal entry
            if not rec.register_ids:
                amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
                move = rec._create_payment_entry(amount)
            else:
                #===================================================================
                amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
                move = self.env['account.move'].create(self._get_move_vals())
                
                total_amount = 0.0
                for line in rec.register_ids:
                    #create receivable or payable each invoice
                    if line.amount_to_pay != 0:
                        rec._create_payment_entry_multi(line.amount_to_pay * (rec.payment_type in ('outbound', 'transfer') and 1 or -1), line.invoice_id, move, line)
                    total_amount += (line.amount_to_pay * (rec.payment_type in ('outbound', 'transfer') and -1 or 1))
#                     #CREATE STATEMENT LINE
#                     if statement_id and line.amount_to_pay != 0:
#                         statement_line_id = StatementLine.create(line._prepare_statement_line_entry(rec, statement_id))
#                         line.write({'statement_line_id': statement_line_id.id})
                #TOTAL AMOUNT
                rec._create_liquidity_entry(total_amount, move)
            #===================================================================
            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()
            
            #print "====rec====",rec.invoice_ids
#             if not rec.sale_id:
#                 rec.write({'sale_id': rec.invoice_ids and rec.invoice_ids.sale_id and rec.invoice_ids.sale_id.id or False})
            rec.write({'state': 'posted', 'move_name': move.name})
            
            
    def _get_counterpart_move_line_vals(self, invoice=False):
        res = super(account_payment, self)._get_counterpart_move_line_vals(invoice=invoice)
        #print "-----self.destination_account_id----",invoice,self,self.destination_account_id
        if invoice and len(invoice) == 1:
            res['account_id'] = invoice.account_id and invoice.account_id.id or self.destination_account_id and self.destination_account_id.id
        return res
    
#     def _create_payment_entry(self, amount):
#         #=======================================================================
#         # CHANGE ORIGINAL _create_payment_entry
#         #=======================================================================
#         """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
#             Return the journal entry.
#         """
#         aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
#         invoice_currency = self.currency_id
# 
#         if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
#             #if all the invoices selected share the same currency, record the paiement in that currency too
#             invoice_currency = self.invoice_ids[0].currency_id
#             #=======================================================================
#             # GET RATE FROM INVOICE DATE
#             debit_inv, credit_inv, amount_currency_inv, currency_inv_id = aml_obj.with_context(date=self.invoice_ids[0].date_invoice)._compute_amount_fields(amount, invoice_currency, self.company_id.currency_id)
#             #=======================================================================
#         
#         debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date, force_rate=self.force_rate)._compute_amount_fields(amount, invoice_currency, self.company_id.currency_id)
#         move = self.env['account.move'].create(self._get_move_vals())
# 
#         #Write line corresponding to invoice payment
#         if self.invoice_ids:
#             counterpart_aml_dict = self._get_shared_move_line_vals(debit_inv, credit_inv, amount_currency_inv, move.id, False)
#         else:
#             counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
#         counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
#         counterpart_aml_dict.update({'currency_id': currency_id})
#         counterpart_aml = aml_obj.create(counterpart_aml_dict)
#         #=======================================================================
#         # CREATE EXCHANGE RATE WHEN PAYMENT FORM INVOICE
#         #=======================================================================
#         if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
#             if self.payment_type == 'inbound':
#                 amount_diff = credit_inv-credit
#             elif self.payment_type == 'outbound':
#                 amount_diff = debit_inv-debit
#             if (amount_diff) != 0:
#                 aml_obj.create({
#                     'name': _('Currency exchange rate difference'),
#                     'debit': amount_diff > 0 and amount_diff or 0.0,
#                     'credit': amount_diff < 0 and -amount_diff or 0.0,
#                     'account_id': amount_diff > 0 and self.company_id.currency_exchange_journal_id.default_debit_account_id.id or self.company_id.currency_exchange_journal_id.default_credit_account_id.id,
#                     'move_id': move.id,
#                     'invoice_id': self.invoice_ids and self.invoice_ids[0].id or False,
#                     'payment_id': self.id,
#                     'currency_id': False,
#                     'amount_currency': 0,
#                     'partner_id': self.invoice_ids and self.invoice_ids[0].partner_id.id,
#                 })
#         #===================================================================
#         #Reconcile with the invoices
#         if self.payment_difference_handling == 'reconcile' and self.payment_difference:
#             writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
#             amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date, force_rate=self.force_rate)._compute_amount_fields(self.payment_difference, invoice_currency, self.company_id.currency_id)[2:]
#             # the writeoff debit and credit must be computed from the invoice residual in company currency
#             # minus the payment amount in company currency, and not from the payment difference in the payment currency
#             # to avoid loss of precision during the currency rate computations. See revision 20935462a0cabeb45480ce70114ff2f4e91eaf79 for a detailed example.
#             total_residual_company_signed = sum(invoice.residual_company_signed for invoice in self.invoice_ids)
#             total_payment_company_signed = self.currency_id.with_context(date=self.payment_date).compute(self.amount, self.company_id.currency_id)
#             if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
#                 amount_wo = total_payment_company_signed - total_residual_company_signed
#             else:
#                 amount_wo = total_residual_company_signed - total_payment_company_signed
#             debit_wo = amount_wo > 0 and amount_wo or 0.0
#             credit_wo = amount_wo < 0 and -amount_wo or 0.0
#             writeoff_line['name'] = _('Counterpart')
#             writeoff_line['account_id'] = self.writeoff_account_id.id
#             writeoff_line['payment_id'] = self.id
#             writeoff_line['debit'] = debit_wo
#             writeoff_line['credit'] = credit_wo
#             writeoff_line['amount_currency'] = amount_currency_wo
#             writeoff_line['currency_id'] = currency_id
#             writeoff_line = aml_obj.create(writeoff_line)
#             if counterpart_aml['debit']:
#                 counterpart_aml['debit'] += credit_wo - debit_wo
#             if counterpart_aml['credit']:
#                 counterpart_aml['credit'] += debit_wo - credit_wo
#             counterpart_aml['amount_currency'] -= amount_currency_wo
#         self.invoice_ids.register_payment(counterpart_aml)
# 
#         #Write counterpart lines
#         if not self.currency_id != self.company_id.currency_id:
#             amount_currency = 0
#         liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
#         liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
#         aml_obj.create(liquidity_aml_dict)
#         #=======================================================================
#         # CREATE JURNAL CHARGE
#         #=======================================================================
#         if self.charge_account_id and self.amount_charges:
#             #if outbound amount_charges(debit), cash/bank(credit) = minus
#             #if inbound amount_charges(credit), cash/bank(credit) = plus
#             amount_charges = self.amount_charges
#             charge_debit, charge_credit, charge_amount_currency, currency_id = aml_obj.with_context(date=self.register_date, force_rate=self.force_rate)._compute_amount_fields(-amount_charges, self.currency_id, self.company_id.currency_id)
#             #Write line corresponding to expense charge
#             charge_counterpart_aml_dict = self.with_context(charge_counter_id=True, charge_liquidity_id=False)._get_shared_move_line_vals(charge_debit, charge_credit, self.advance_type == 'cash' and -charge_amount_currency or charge_amount_currency, move.id, False)
#             charge_counterpart_aml_dict.update(self.with_context(charge_ref='ADM')._get_counterpart_move_line_vals(self.invoice_ids))
#             charge_counterpart_aml_dict.update({'account_id': self.charge_account_id.id, 'currency_id': currency_id})
#             charge_counterpart_aml = aml_obj.create(charge_counterpart_aml_dict)
#             #Write counterpart lines with cash/bank account
#             if not self.currency_id != self.company_id.currency_id:
#                 charge_amount_currency = 0
#             charge_liquidity_aml_dict = self.with_context(charge_counter_id=False, charge_liquidity_id=True)._get_shared_move_line_vals(charge_credit, charge_debit, self.advance_type == 'cash' and charge_amount_currency or -charge_amount_currency, move.id, False)
#             charge_liquidity_aml_dict.update(self.with_context(charge_ref='ADM', charge_account_id=True)._get_liquidity_move_line_vals(amount_charges))
#             aml_obj.create(charge_liquidity_aml_dict)
#         #=======================================================================
#         # CREATE JOURNAL OTHER ACCOUNT
#         #=======================================================================
#         if self.other_lines and self.advance_type == 'cash':
#             for other in self.other_lines:
#                 amount_others = other.amount
#                 other_debit, other_credit, other_amount_currency, currency_id = aml_obj.with_context(date=self.register_date, force_rate=self.force_rate)._compute_amount_fields(-amount_others, self.currency_id, self.company_id.currency_id)
#                 #Write line corresponding to expense other
#                 other_counterpart_aml_dict = self.with_context(other_counter_id=True, other_liquidity_id=False)._get_shared_move_line_vals(other_debit, other_credit, -other_amount_currency, move.id, False)
#                 other_counterpart_aml_dict.update(self.with_context(other_ref='ADM')._get_counterpart_move_line_vals(self.invoice_ids))
#                 other_counterpart_aml_dict.update({'account_id': other.account_id.id, 'currency_id': currency_id})
#                 other_counterpart_aml = aml_obj.create(other_counterpart_aml_dict)
#                 #Write counterpart lines with cash/bank account
#                 if not self.currency_id != self.company_id.currency_id:
#                     other_amount_currency = 0
#                 other_liquidity_aml_dict = self.with_context(other_counter_id=False, other_liquidity_id=True)._get_shared_move_line_vals(other_credit, other_debit, other_amount_currency, move.id, False)
#                 other_liquidity_aml_dict.update(self.with_context(other_ref='ADM', account_id=True)._get_liquidity_move_line_vals(amount_others))
#                 aml_obj.create(other_liquidity_aml_dict)
#         #=======================================================================
#         move.post()
#         return move
    
#     def _get_move_transfer_vals(self, journal=None):
#         """ Return dict to create the payment move
#         """
#         journal = journal or self.journal_id
#         if not journal.sequence_id:
#             raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
#         if not journal.sequence_id.active:
#             raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
#         name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
#         return {
#             'name': name,
#             'date': self.register_date,
#             'ref': self.communication or '',
#             'company_id': self.company_id.id,
#             'journal_id': journal.id,
#         }
            
    
    @api.multi
    def post_multi(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':                        
                        if rec.advance_type == 'advance':
                            sequence_code = 'account.payment.customer.advance'
                        else:
                            sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        if rec.advance_type == 'advance':
                            sequence_code = 'account.payment.supplier.advance'
                        else:
                            sequence_code = 'account.payment.supplier.invoice'
                            
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
#             Statement = self.env['account.bank.statement']
#             StatementLine = self.env['account.bank.statement.line']
#             statement_id = Statement.search([('journal_id','=',rec.journal_id.id),
#                                              ('date','>=',rec.payment_date),
#                                              ('date','<=',rec.payment_date)], limit=1)
#             if not statement_id:
#                 statement_id = Statement.create({'journal_id': rec.journal_id.id, 'date': rec.payment_date})
            # Create the journal entry
            #amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            #move = rec._create_payment_entry(amount)
            
            #amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            #move = self.env['account.move'].create(self._get_move_vals())
            
            #total_amount = 0.0
            #for line in rec.register_ids:
                #create receivable or payable each invoice
                #if line.action:
                #rec._create_payment_entry_multi(line.amount_to_pay * (rec.payment_type in ('outbound', 'transfer') and 1 or -1), line.invoice_id, move, line)
                #total_amount += (line.amount_to_pay * (rec.payment_type in ('outbound', 'transfer') and -1 or 1))
            #TOTAL AMOUNT
            #rec._create_liquidity_entry(total_amount, move)
            # Create the journal entry
            if not rec.register_ids:
                amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
                move = rec._create_payment_entry(amount)
            else:
                #===================================================================
                amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
                move = self.env['account.move'].create(self._get_move_vals())
                
                total_amount = 0.0
                for line in rec.register_ids:
                    #create receivable or payable each invoice
                    if line.amount_to_pay != 0:
                        rec._create_payment_entry_multi(line.amount_to_pay * (rec.payment_type in ('outbound', 'transfer') and 1 or -1), line.invoice_id, move, line)
                    total_amount += (line.amount_to_pay * (rec.payment_type in ('outbound', 'transfer') and -1 or 1))
                    #===========================================================
                    # #CREATE STATEMENT LINE
                    # if statement_id and line.amount_to_pay != 0:
                    #     statement_line_id = StatementLine.create(line._prepare_statement_line_entry(rec, statement_id))
                    #     line.write({'statement_line_id': statement_line_id.id})
                    #===========================================================
                #TOTAL AMOUNT
                rec._create_liquidity_entry(total_amount, move)
            #===================================================================
            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()
            rec.write({'state': 'posted', 'move_name': move.name})
            
    def _create_payment_entry_multi(self, amount, invoice, move, line):
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = invoice.currency_id# or self.currency_id
        debit, credit, amount_currency, currency_id  = aml_obj.with_context(date=self.payment_date, force_rate=self.force_rate)._compute_amount_fields(amount, invoice_currency, self.company_id.currency_id)
        #=======================================================================
        # GET RATE FROM INVOICE DATE
        debit_inv, credit_inv, amount_currency_inv, currency_inv_id = aml_obj.with_context(date=invoice.date_invoice)._compute_amount_fields(amount, invoice_currency, self.company_id.currency_id)
        #=======================================================================
        #Write line corresponding to invoice payment
        if invoice:
            counterpart_aml_dict = self._get_shared_move_line_vals(debit_inv, credit_inv, amount_currency_inv, move.id, False)
        else:
            counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        #counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, invoice)
        #print "===counterpart_aml_dict===",line.invoice_id
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(line.invoice_id))
        counterpart_aml_dict.update({'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)
        #=======================================================================
        # CREATE EXCHANGE RATE ONLY FOR PARTIAL PAYMENT
        #=======================================================================
        if self.payment_type == 'inbound':
            amount_diff = credit_inv-credit
        elif self.payment_type == 'outbound':
            amount_diff = debit_inv-debit
        if (amount_diff) != 0:
            exch_diff = {
                'name': _('Currency exchange rate difference'),
                'debit': amount_diff > 0 and amount_diff or 0.0,
                'credit': amount_diff < 0 and -amount_diff or 0.0,
                'account_id': amount_diff > 0 and self.company_id.currency_exchange_journal_id.default_debit_account_id.id or self.company_id.currency_exchange_journal_id.default_credit_account_id.id,
                'move_id': move.id,
                'invoice_id': invoice and invoice.id or False,
                'payment_id': self.id,
                'currency_id': False,
                'amount_currency': 0,
                'partner_id': invoice and invoice.partner_id.id,
            }
            aml_obj.create(exch_diff)
        #===================================================================
        #Reconcile with the invoices each
        if line.payment_difference and line.writeoff_account_id:
            if not invoice_currency:
                invoice_currency = line.currency_id
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date, force_rate=self.force_rate)._compute_amount_fields(line.payment_difference, invoice_currency, self.company_id.currency_id)[2:]
            # the writeoff debit and credit must be computed from the invoice residual in company currency
            # minus the payment amount in company currency, and not from the payment difference in the payment currency
            # to avoid loss of precision during the currency rate computations. See revision 20935462a0cabeb45480ce70114ff2f4e91eaf79 for a detailed example.
            total_residual_company_signed = line.invoice_id.residual_company_signed#sum(invoice.residual_company_signed for invoice in self.invoice_ids)
            total_payment_company_signed = self.currency_id.with_context(date=self.payment_date).compute(line.amount_to_pay, self.company_id.currency_id)
            if line.invoice_id.type in ['in_invoice', 'out_refund']:
                amount_wo = total_payment_company_signed - total_residual_company_signed
            else:
                amount_wo = total_residual_company_signed - total_payment_company_signed
            debit_wo = amount_wo > 0 and amount_wo or 0.0
            credit_wo = amount_wo < 0 and -amount_wo or 0.0
            writeoff_line['name'] = _('Counterpart')
            writeoff_line['account_id'] = line.writeoff_account_id.id
            writeoff_line['payment_id'] = self.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit']:
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit']:
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo
            #self.invoice_ids.register_payment(counterpart_aml)
            print ("===WITH WRITEOFF===")
            if invoice:
                invoice.register_payment(counterpart_aml, line.writeoff_account_id, self.journal_id)
            else:
                if not invoice and line.move_line_id:
                    (line.move_line_id + counterpart_aml).reconcile(line.writeoff_acc_id, self.journal_id)
        else:
            print ("===NOT WRITEOFF===")
            if invoice:
                print ("==register_payment==",counterpart_aml)
                invoice.register_payment(counterpart_aml)
            else:
                if not invoice and line.move_line_id:
                    print ("====",line.move_line_id,counterpart_aml)
                    (line.move_line_id + counterpart_aml).reconcile()
    
    def _get_counterpart_register_vals(self, registers=False):
        name = ''
        if registers:
            name += ''
            for reg in registers:
                if reg.name:
                    name += reg.name + ', '
            name = name[:len(name)-2] 
        return {
            'name': name,
            'account_id': self.destination_account_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
            'payment_id': self.id,
        }
    
    def _create_liquidity_entry(self, total_amount, move):
        """ def _create_liquidity_entry_aos for total liquidity received or paid"""
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        #invoice_currency = invoice.currency_id
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date, force_rate=self.force_rate)._compute_amount_fields(total_amount, self.currency_id, self.company_id.currency_id)
        #print "----_create_liquidity_entry_aos----",debit, credit, amount_currency
        liquidity_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(total_amount))
        aml_obj.create(liquidity_aml_dict)
        move.post()
        return move
    
#     
#     def _get_counterpart_move_line_vals(self, invoice=False):
#         
#         if self.payment_type == 'transfer':
#             name = self.name
#         else:
#             name = ''
#             if self.partner_type == 'customer':
#                 if self.payment_type == 'inbound':
#                     name += _("Customer Payment")
#                 elif self.payment_type == 'outbound':
#                     name += _("Customer Refund")
#             elif self.partner_type == 'supplier':
#                 if self.payment_type == 'inbound':
#                     name += _("Vendor Refund")
#                 elif self.payment_type == 'outbound':
#                     name += _("Vendor Payment")
#             if invoice:
#                 name += ': '
#                 for inv in invoice:
#                     if inv.move_id:
#                         name += inv.number + ', '
#                 name = name[:len(name)-2] 
#         return {
#             'name': name,
#             'account_id': self.destination_account_id.id,
#             'journal_id': self.journal_id.id,
#             'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
#             'payment_id': self.id,
#         }
    
class account_payment_line(models.Model):
    _name = 'account.payment.line'
    _description = 'Account Payment Line'
    
    def _compute_total_invoices_amount(self):
        """ Compute the sum of the residual of invoices, expressed in the payment currency """
        payment_currency = self.currency_id or self.payment_id.journal_id.currency_id or self.payment_id.journal_id.company_id.currency_id or self.env.user.company_id.currency_id
        if self.move_line_id.company_id.currency_id != payment_currency:
            total = self.move_line_id.company_currency_id.with_context(date=self.payment_id.payment_date).compute(self.move_line_id.amount_residual, payment_currency)
        else:
            total = self.move_line_id.amount_residual
        return abs(total)
    
    @api.one
    @api.depends('move_line_id', 'invoice_id', 'amount_to_pay', 'payment_id.payment_date', 'currency_id')
    def _compute_payment_difference(self):
        self.payment_difference = self._compute_total_invoices_amount() - self.amount_to_pay
#         if self.type == 'dr':
#             self.payment_difference = self._compute_total_invoices_amount() - self.amount_to_pay
#         else:
#             self.payment_difference = self._compute_total_invoices_amount() + self.amount_to_pay
            
    @api.one
    @api.depends('invoice_id', 'move_line_id')
    def _compute_invoice_currency(self):
        if self.invoice_id and self.invoice_id.currency_id:
            self.move_currency_id = self.invoice_id.currency_id.id
        else:
            self.move_currency_id = self.move_line_id.currency_id.id
            
    move_line_id = fields.Many2one('account.move.line', string='Move Line')
    move_currency_id = fields.Many2one('res.currency', string='Invoice Currency', compute='_compute_invoice_currency',)
    date = fields.Date('Invoice Date')
    date_due = fields.Date('Due Date')
    type = fields.Selection([('dr', 'Debit'),('cr','Credit')], 'Type')
    payment_id = fields.Many2one('account.payment', string='Payment')
    payment_currency_id = fields.Many2one('res.currency', string='Currency')
    currency_id = fields.Many2one('res.currency', related='payment_id.currency_id', string='Currency')
    name = fields.Char(string='Description', required=True)
    invoice_id = fields.Many2one('account.invoice', string='Invoice')
    amount_total = fields.Float('Original Amount', required=True, digits=dp.get_precision('Account'))
    residual = fields.Float('Outstanding Amount', required=True, digits=dp.get_precision('Account'))
    reconcile = fields.Boolean('Full Payment')
    amount_to_pay = fields.Float('Allocation', required=True, digits=dp.get_precision('Account'))
    statement_line_id = fields.Many2one('account.bank.statement.line', string='Statement Line')
    payment_difference = fields.Monetary(compute='_compute_payment_difference', string='Payment Difference', readonly=True, store=True)
    payment_difference_handling = fields.Selection([('open', 'Keep open'), 
                                                    ('reconcile', 'Full Payment')], 
                                                   default='open', string="Write-off", copy=False)
    writeoff_account_id = fields.Many2one('account.account', string="Write-off Account", domain=[('deprecated', '=', False)], copy=False)
    action = fields.Boolean('To Pay')
    
#     @api.onchange('action')
#     def _onchange_action(self):
#         self.amount_to_pay = self.action and self.residual or 0.0
        
    def _prepare_statement_line_entry(self, payment, statement):
        #print "===payment===",payment.name
        values = {
            'statement_id': statement.id,
            'payment_line_id': self.id,
            'date': payment.payment_date,
            'name': self.invoice_id.number or self.move_line_id.name or '/', 
            'partner_id': payment.partner_id.id,
            'ref': payment.name,
            'amount': self.amount_to_pay,
        }
        return values

class account_payment_other(models.Model):
    _name = 'account.payment.other'
    _description = 'Account Payment Others'
    
    payment_id = fields.Many2one('account.payment', string='Payment')
    name = fields.Char(string='Description', required=True)
    account_id = fields.Many2one('account.account', string='Account',
        required=False, domain=[('deprecated', '=', False),('user_type_id.type','=','other')],
        help="The income or expense account related to the selected product.")
    account_analytic_id = fields.Many2one('account.analytic.account',
        string='Analytic Account')
    company_id = fields.Many2one('res.company', string='Company',
        related='payment_id.company_id', store=True, readonly=True)
    amount = fields.Float('Amount', required=True, digits=dp.get_precision('Account'))
    
# class AccountBankStatementLine(models.Model):
#     _inherit = 'account.bank.statement.line'
#     
#     payment_line_id = fields.Many2one('account.payment.line', string='Payment Line')
    