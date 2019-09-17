# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import models, fields, api, _
from odoo.tools import float_round, float_is_zero
from odoo.exceptions import UserError, ValidationError
import openerp.addons.decimal_precision as dp

# class account_abstract_payment(models.AbstractModel):
#     _inherit = "account.abstract.payment"
#      
#     @api.one
#     @api.constrains('amount')
#     def _check_amount(self):
#         #STRING ALLOWED FOR NEGATIVE AMOUNT
#         #if not self.amount > 0.0 and not (self.register_ids or self.settlement_ids or self.other_lines):
#         #    raise ValidationError('The payment amount must be strictly positive.')
#         return

    
class account_payment(models.Model):
    _inherit = "account.payment"
    
#     @api.depends('journal_id')
#     def _compute_branch_id(self):
#         for payment in self:
#             if payment.journal_id:
#                 payment.branch_id = payment.journal_id.branch_id
#                 
#             
#     @api.one
#     def _amount2text_idr(self):
#         for payment in self:
#             if payment.currency_id:
#                 self.check_amount_in_words_id = ''#amount_to_text_id.amount_to_text(math.floor(payment.amount_subtotal), 'id', payment.currency_id.name)
#             else:
#                 self.check_amount_in_words_id = amount_to_text_en.amount_to_text(math.floor(payment.amount_subtotal), lang='en', currency='')
#         return self.check_amount_in_words_id
    
#     register_date = fields.Date(string='Register Date', required=False, copy=False)
    advance_type = fields.Selection([('invoice', 'Reconcile to Invoice'), 
                                     ('advance', 'Down Payment'), 
                                     ('advance_emp', 'Employee Advance'),
                                     ('receivable_emp','Employee Receivable')], default='invoice', string='Type')
    is_force_curr = fields.Boolean('Kurs Nego')
    force_rate = fields.Monetary('Kurs Nego Amount')
    register_date = fields.Date(string='Register Date',  default=fields.Date.context_today, required=False, copy=False)
    state = fields.Selection(selection_add=[('confirm', 'Confirm'),('receipt','Receipt')])
    #================make charge transfer=======================================
    amount_charges = fields.Monetary(string='Amount Adm', required=False)
    charge_account_id = fields.Many2one('account.account', string='Account Adm', domain=[('user_type_id.name','=','601.00 Expenses')])
    payment_adm = fields.Selection([
            ('cash','Cash'),
            ('free_transfer','Non Payment Administration Transfer'),
            ('transfer','Transfer'),
            #('check','Check/Giro'),
            #('letter','Letter Credit'),
            ('cc','Credit Card'),
            ('dc','Debit Card'),
            ],string='Payment Adm')
    card_number = fields.Char('Card Number', size=128, required=False)
    card_type = fields.Selection([
            ('visa','Visa'),
            ('master','Master'),
            ('bca','BCA Card'),
            ('citi','CITI Card'),
            ('amex','AMEX'),
            ], string='Card Type', size=128)
    
    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'draft' and self.payment_type == 'transfer':
            return 'aos_account_transfer.mt_transfer_created'
        elif 'state' in init_values and self.state == 'confirm' and self.payment_type == 'transfer':
            return 'aos_account_transfer.mt_transfer_confirm'
        elif 'state' in init_values and self.state == 'sent' and self.payment_type == 'transfer':
            return 'aos_account_transfer.mt_transfer_sent'
        elif 'state' in init_values and self.state == 'receipt' and self.payment_type == 'transfer':
            return 'aos_account_transfer.mt_transfer_receipt'
        return super(account_payment, self)._track_subtype(init_values)
# 
#     def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
#         context = dict(self._context or {})
#         if context.get('charge_counter_id') or context.get('charge_liquidity_id'):
#             res = super(account_payment, self)._get_shared_move_line_vals(credit, debit, amount_currency, move_id, invoice_id)
#             res['name'] = 'BIAYA ADMIN'
#         else:
#             res = super(account_payment, self)._get_shared_move_line_vals(debit, credit, amount_currency, move_id, invoice_id)
#         res['partner_id'] = (self.payment_type in ('inbound', 'outbound') or self.advance_type == 'advance_emp') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False
#         res['branch_id'] = self.destination_journal_id.branch_id.id or False
#         return res
#     
#     def _get_counterpart_move_line_vals(self, invoice=False):
#         res = super(account_payment, self)._get_counterpart_move_line_vals(invoice=invoice)
#         if invoice and len(invoice) == 1:
#             res['branch_id'] = invoice.branch_id.id or False
#         else:
#             res['branch_id'] = self.branch_id.id or False
#         return res
#     
#     
#     def _get_liquidity_move_line_vals(self, amount):
#         res = super(account_payment, self)._get_liquidity_move_line_vals(amount)
#         res['branch_id'] = self.journal_id.branch_id.id or False
#         return res

    def confirm(self):
        for rec in self:
            rec.state = 'confirm'
            
    def _get_move_transfer_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        return {
            'name': name,
            'date': self.register_date,
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }
            
    def _create_transfer_from_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        #=======================================================================
        # CREATE JURNAL TRANSFER TO CROSS ACCOUNT
        #=======================================================================
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.register_date, force_rate=self.force_rate)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)
        move = self.env['account.move'].create(self._get_move_transfer_vals())
        #Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        #print "==self.advance_type==",self._get_counterpart_register_vals(self.register_ids)
        if self.advance_type == 'advance_emp':
            counterpart_aml_dict.update(self._get_counterpart_register_vals(self.register_ids))
        else:
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)
        #Write counterpart lines
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml_obj.create(liquidity_aml_dict)
        #=======================================================================
        # CREATE JURNAL CHARGE
        #=======================================================================
        if self.charge_account_id and self.amount_charges:
            amount_charges = self.amount_charges
            charge_debit, charge_credit, charge_amount_currency, currency_id = aml_obj.with_context(date=self.register_date, force_rate=self.force_rate)._compute_amount_fields(-amount_charges, self.currency_id, self.company_id.currency_id)
            #Write line corresponding to expense charge
            charge_counterpart_aml_dict = self._get_shared_move_line_vals(charge_debit, charge_credit, charge_amount_currency, move.id, False)
            charge_counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            charge_counterpart_aml_dict.update({'account_id': self.charge_account_id.id, 'currency_id': currency_id})
            charge_counterpart_aml = aml_obj.create(charge_counterpart_aml_dict)
            #print "====charge_counterpart_aml_dict===",charge_counterpart_aml_dict
            #Write counterpart lines with cash/bank account
            if not self.currency_id != self.company_id.currency_id:
                charge_amount_currency = 0
            charge_liquidity_aml_dict = self._get_shared_move_line_vals(charge_credit, charge_debit, -charge_amount_currency, move.id, False)
            charge_liquidity_aml_dict.update(self._get_liquidity_move_line_vals(amount_charges))
            aml_obj.create(charge_liquidity_aml_dict)
            #print "====charge_liquidity_aml_dict===",charge_liquidity_aml_dict
        #=======================================================================
        # POST MOVE
        #=======================================================================
        move.post()
        return move

    def _create_payment_entry(self, amount):
        #=======================================================================
        # CHANGE ORIGINAL _create_payment_entry
        #=======================================================================
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = self.currency_id

        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            #if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id
            #=======================================================================
            # GET RATE FROM INVOICE DATE
            debit_inv, credit_inv, amount_currency_inv, currency_inv_id = aml_obj.with_context(date=self.invoice_ids[0].date_invoice)._compute_amount_fields(amount, invoice_currency, self.company_id.currency_id)
            #=======================================================================
        
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date, force_rate=self.force_rate)._compute_amount_fields(amount, invoice_currency, self.company_id.currency_id)
        move = self.env['account.move'].create(self._get_move_vals())

        #Write line corresponding to invoice payment
        if self.invoice_ids:
            counterpart_aml_dict = self._get_shared_move_line_vals(debit_inv, credit_inv, amount_currency_inv, move.id, False)
        else:
            counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)
        #=======================================================================
        # CREATE EXCHANGE RATE WHEN PAYMENT FORM INVOICE
        #=======================================================================
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            if self.payment_type == 'inbound':
                amount_diff = credit_inv-credit
            elif self.payment_type == 'outbound':
                amount_diff = debit_inv-debit
            if (amount_diff) != 0:
                aml_obj.create({
                    'name': _('Currency exchange rate difference'),
                    'debit': amount_diff > 0 and amount_diff or 0.0,
                    'credit': amount_diff < 0 and -amount_diff or 0.0,
                    'account_id': amount_diff > 0 and self.company_id.currency_exchange_journal_id.default_debit_account_id.id or self.company_id.currency_exchange_journal_id.default_credit_account_id.id,
                    'move_id': move.id,
                    'invoice_id': self.invoice_ids and self.invoice_ids[0].id or False,
                    'payment_id': self.id,
                    'currency_id': False,
                    'amount_currency': 0,
                    'partner_id': self.invoice_ids and self.invoice_ids[0].partner_id.id,
                })
        #===================================================================
        #Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date, force_rate=self.force_rate)._compute_amount_fields(self.payment_difference, invoice_currency, self.company_id.currency_id)[2:]
            # the writeoff debit and credit must be computed from the invoice residual in company currency
            # minus the payment amount in company currency, and not from the payment difference in the payment currency
            # to avoid loss of precision during the currency rate computations. See revision 20935462a0cabeb45480ce70114ff2f4e91eaf79 for a detailed example.
            total_residual_company_signed = sum(invoice.residual_company_signed for invoice in self.invoice_ids)
            total_payment_company_signed = self.currency_id.with_context(date=self.payment_date).compute(self.amount, self.company_id.currency_id)
            if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
                amount_wo = total_payment_company_signed - total_residual_company_signed
            else:
                amount_wo = total_residual_company_signed - total_payment_company_signed
            debit_wo = amount_wo > 0 and amount_wo or 0.0
            credit_wo = amount_wo < 0 and -amount_wo or 0.0
            writeoff_line['name'] = _('Counterpart')
            writeoff_line['account_id'] = self.writeoff_account_id.id
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
        self.invoice_ids.register_payment(counterpart_aml)

        #Write counterpart lines
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml_obj.create(liquidity_aml_dict)
        #=======================================================================
        # CREATE JURNAL CHARGE
        #=======================================================================
        if self.charge_account_id and self.amount_charges:
            #if outbound amount_charges(debit), cash/bank(credit) = minus
            #if inbound amount_charges(credit), cash/bank(credit) = plus
            amount_charges = self.amount_charges
            charge_debit, charge_credit, charge_amount_currency, currency_id = aml_obj.with_context(date=self.register_date, force_rate=self.force_rate)._compute_amount_fields(-amount_charges, self.currency_id, self.company_id.currency_id)
            #Write line corresponding to expense charge
            charge_counterpart_aml_dict = self.with_context(charge_counter_id=True, charge_liquidity_id=False)._get_shared_move_line_vals(charge_debit, charge_credit, self.advance_type == 'cash' and -charge_amount_currency or charge_amount_currency, move.id, False)
            charge_counterpart_aml_dict.update(self.with_context(charge_ref='ADM')._get_counterpart_move_line_vals(self.invoice_ids))
            charge_counterpart_aml_dict.update({'account_id': self.charge_account_id.id, 'currency_id': currency_id})
            charge_counterpart_aml = aml_obj.create(charge_counterpart_aml_dict)
            #Write counterpart lines with cash/bank account
            if not self.currency_id != self.company_id.currency_id:
                charge_amount_currency = 0
            charge_liquidity_aml_dict = self.with_context(charge_counter_id=False, charge_liquidity_id=True)._get_shared_move_line_vals(charge_credit, charge_debit, self.advance_type == 'cash' and charge_amount_currency or -charge_amount_currency, move.id, False)
            charge_liquidity_aml_dict.update(self.with_context(charge_ref='ADM', charge_account_id=True)._get_liquidity_move_line_vals(amount_charges))
            aml_obj.create(charge_liquidity_aml_dict)
        #=======================================================================
        # CREATE JOURNAL OTHER ACCOUNT
        #=======================================================================
        if self.other_lines and self.advance_type == 'cash':
            for other in self.other_lines:
                amount_others = other.amount
                other_debit, other_credit, other_amount_currency, currency_id = aml_obj.with_context(date=self.register_date, force_rate=self.force_rate)._compute_amount_fields(-amount_others, self.currency_id, self.company_id.currency_id)
                #Write line corresponding to expense other
                other_counterpart_aml_dict = self.with_context(other_counter_id=True, other_liquidity_id=False)._get_shared_move_line_vals(other_debit, other_credit, -other_amount_currency, move.id, False)
                other_counterpart_aml_dict.update(self.with_context(other_ref='ADM')._get_counterpart_move_line_vals(self.invoice_ids))
                other_counterpart_aml_dict.update({'account_id': other.account_id.id, 'currency_id': currency_id})
                other_counterpart_aml = aml_obj.create(other_counterpart_aml_dict)
                #Write counterpart lines with cash/bank account
                if not self.currency_id != self.company_id.currency_id:
                    other_amount_currency = 0
                other_liquidity_aml_dict = self.with_context(other_counter_id=False, other_liquidity_id=True)._get_shared_move_line_vals(other_credit, other_debit, other_amount_currency, move.id, False)
                other_liquidity_aml_dict.update(self.with_context(other_ref='ADM', account_id=True)._get_liquidity_move_line_vals(amount_others))
                aml_obj.create(other_liquidity_aml_dict)
        #=======================================================================
        move.post()
        return move
    #===========================================================================
    # internal transfer
    #===========================================================================
    @api.multi
    def post_transfer(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            #CHANGE STATE CONFIRM WHICH CAN BE POSTED
            if rec.state != 'confirm':
                raise UserError(_("Only a confirm transfer can be posted. Trying to post a payment in state %s.") % rec.state)

            # Use the right sequence to set the name
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.register_date).next_by_code('account.payment.transfer')

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_transfer_from_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.

            rec.write({'state': 'sent', 'move_name': move.name})
    
    @api.multi
    def post_receipt(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            #CHANGE STATE SENT WHICH CAN BE POSTED
            if rec.state != 'sent':
                raise UserError(_("Only a sent transfer can be posted. Trying to post a payment in state %s.") % rec.state)

            # Use the right sequence to set the name
            # Use the right sequence to set the name
            #rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code('account.payment.transfer')

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = rec.move_line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.write({'state': 'receipt'})
    