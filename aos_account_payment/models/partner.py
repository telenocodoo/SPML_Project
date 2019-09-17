# -*- coding: utf-8 -*-

from operator import itemgetter
import time

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
    
class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Partner'
    
    property_account_advance_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Advance Customer", 
        domain="[('internal_type', '=', 'other'), ('reconcile', '=', True)]",
        help="This account will be used instead of the default one as the receivable advance account for the current partner",
        required=False)
    property_account_advance_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Advance Vendors",
        domain="[('internal_type', '=', 'other'), ('reconcile', '=', True)]",
        help="This account will be used instead of the default one as the payable advance account for the current partner",
        required=False)
    property_journal_installment_id = fields.Many2one('account.journal', company_dependent=True, string='Journal Installment', 
          required=False,  domain=[('type', '=', 'sale')])
    property_account_employee_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable Employee",
        domain="[('internal_type', '=', 'other'), ('reconcile', '=', True)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=False)
    property_account_employee_advance_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Advance Employee",
        domain="[('internal_type', '=', 'other'), ('reconcile', '=', True)]",
        help="This account will be used instead of the default one as the payable advance account for the current partner",
        required=False)
    #IF DEPOSIT NEEDED
    property_account_deposit_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Deposit Customer", 
        domain="[('internal_type', '=', 'other'), ('reconcile', '=', True)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=False)
    property_account_deposit_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Deposit Vendors",
        domain="[('internal_type', '=', 'other'), ('reconcile', '=', True)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=False)
    