# -*- coding: utf-8 -*-

from odoo import models, fields, api


PAY_LINES_PER_PAGE = 20


class PrintBatchPayment(models.AbstractModel):
    _inherit = 'report.account_batch_payment.print_batch_payment'

    def get_pages(self, batch):
        """ Returns the data structure used by the template
        """
        i = 0
        payment_slices = []
        while i < len(batch.payment_ids):
            payment_slices.append(batch.payment_ids[i:i+PAY_LINES_PER_PAGE])
            i += PAY_LINES_PER_PAGE
        print("hi .." ,payment_slices)
        invoice_list =[]
        for x in batch.payment_ids:
           invoice_list.append(x.communication )

        print(invoice_list)
        Journals=self.get_total_data(invoice_list)
        print("shalby .. ",Journals)
        list_payments=[{
            'ID':batch.id,
            'date': batch.date,
            'batch_name': batch.name,
            'journal_name': batch.journal_id.name,
            'payments': payments,
            'currency': batch.currency_id,
            'total_amount': batch.amount,
            'footer': batch.journal_id.company_id.report_footer,
            'Invoices':self.get_total_data(invoice_list),
        } for payments in payment_slices]




        print("hi2.. ",list_payments)

        return [{
            'date': batch.date,
            'batch_name': batch.name,
            'journal_name': batch.journal_id.name,
            'payments': payments,
            'currency': batch.currency_id,
            'total_amount': batch.amount,
            'footer': batch.journal_id.company_id.report_footer,
            'Invoices': self.get_total_data(invoice_list),
        } for payments in payment_slices]

    @api.model
    def _get_report_values(self, docids, data=None):
        report_name = 'account_batch_payment.print_batch_payment'
        report = self.env['ir.actions.report']._get_report_from_name(report_name)
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
            'pages': self.get_pages,
        }

    @api.multi
    def get_total_data(self, invoice_list):
        lst = []
        journals = []
        journal_item_id = self.env['account.move.line']
        # for record in self:
        journal_ids = journal_item_id.search([('ref', 'in', invoice_list)])
        #print("invoice_list ..",invoice_list)
        #print(journal_ids)
        if journal_ids:
            for line in journal_ids:
                vals = {
                    'name': line.move_id.name,
                    'date': line.date,
                    'label': line.name,
                    'debit': line.debit,
                    'credit': line.credit,
                }
                lst.append(vals)
                if line.move_id.name not in journals:
                    journals.append(line.move_id.name)
        print("lst: ", lst)
        print("journals: ", journals)
        return lst



#
# class BatchPayment(models.Model):
#     _inherit = 'account.batch.payment'
#
#
#     def get_pages(self, batch):
#         """ Returns the data structure used by the template
#         """
#         i = 0
#         payment_slices = []
#         while i < len(batch.payment_ids):
#             payment_slices.append(batch.payment_ids[i:i+PAY_LINES_PER_PAGE])
#             i += PAY_LINES_PER_PAGE
#         print("hi .." ,payment_slices)
#         list_payments=[{
#             'ID':batch.id,
#             'date': batch.date,
#             'batch_name': batch.name,
#             'journal_name': batch.journal_id.name,
#             'payments': payments,
#             'currency': batch.currency_id,
#             'total_amount': batch.amount,
#             'footer': batch.journal_id.company_id.report_footer,
#         } for payments in payment_slices]
#         print("hi2.. ",list_payments)
#
#
#
#
#
#         return [{
#             'ID':batch.id,
#             'date': batch.date,
#             'batch_name': batch.name,
#             'journal_name': batch.journal_id.name,
#             'payments': payments,
#             'currency': batch.currency_id,
#             'total_amount': batch.amount,
#             'footer': batch.journal_id.company_id.report_footer,
#         } for payments in payment_slices]
#
#     @api.multi
#     def get_total_data(self,invoice_no):
#         lst = []
#         journals = []
#         journal_item_id = self.env['account.move.line']
#         # for record in self:
#         journal_ids = journal_item_id.search([('ref', 'in', ['INV/2019/0013', 'INV/2019/0002/02'])])
#         if journal_ids:
#             for line in journal_ids:
#                 vals = {
#                     'name': line.move_id.name,
#                     'date': line.date,
#                     'label': line.name,
#                     'debit': line.debit,
#                     'credit': line.credit,
#                     }
#                 lst.append(vals)
#                 if line.move_id.name not in journals:
#                     journals.append(line.move_id.name)
#         print("lst: ", lst)
#         print("journals: ", journals)
#         return lst
#
#     @api.multi
#     def get_total_journals(self):
#         # print(self.id)
#         journals = []
#         journal_item_id = self.env['account.move.line']
#         journal_ids = journal_item_id.search([('ref', 'in', ['INV/2019/0003/03', 'INV/2019/0002/02'])])
#         if journal_ids:
#             for line in journal_ids:
#                 if line.move_id.name not in journals:
#                     journals.append(line.move_id.name)
#         print("journals: ", journals)
#         return journals
#
#     @api.multi
#     def get_total_amount(self):
#         debit = []
#         # total = 0.0
#         # credit = []
#         journal_item_id = self.env['account.move.line']
#         journal_ids = journal_item_id.search([('ref', 'in', ['INV/2019/0003/03', 'INV/2019/0002/02'])])
#         if journal_ids:
#             for line in journal_ids:
#                 vals = {
#                         'debit': line.invoice_id.amount_total,
#                 }
#                 debit.append(vals)
#                 # debit.append()
#                 # credit.append(line.invoice_id.amount_total)
#
#         # for i in debit:
#         #     total += i
#         print("debit: ", debit)
#         # print("total: ", total)
#         return debit
