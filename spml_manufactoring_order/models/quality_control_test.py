# -*- coding: utf-8 -*-

from odoo import models, fields, api


class QuestionType(models.Model):
    _name = "question.type"
    name = fields.Char()
    question_type = fields.Selection(selection=[('quantitative', 'Quantitative'),
                                                ('qualitative', 'qualitative'), ])
    q_from = fields.Float(string="Quantity From")
    q_to = fields.Float(string="Quantity To")
    specification = fields.Char()


class QualitativeValue(models.Model):
    _name = "qualitative.value"
    name = fields.Char()


class QualityCheckTest(models.Model):
    _name = "quality.check.test"
    _rec_name = 'product_id'

    product_id = fields.Many2one("product.product")
    quality_test_ids = fields.One2many("quality.test.lines", "quality_check_id")


class QualityTestLines(models.Model):
    _name = "quality.test.lines"

    quality_check_id = fields.Many2one("quality.check.test")
    quality_test_id = fields.Many2one("quality.check")
    question_id = fields.Many2one("question.type")
    question_type = fields.Selection(selection=[('quantitative', 'Quantitative'),
                                                ('qualitative', 'qualitative'), ])
    quantitative_value = fields.Float()
    qualitative_id = fields.Many2one(comodel_name="qualitative.value", string="qualitative value")
    q_from = fields.Float()
    q_to = fields.Float()
    specification = fields.Char()
    is_success = fields.Boolean(compute='get_success_value')

    @api.onchange('question_id')
    def get_question_data(self):
        self.question_type = self.question_id.question_type
        self.q_from = self.question_id.q_from
        self.q_to = self.question_id.q_to
        self.specification = self.question_id.specification

    @api.depends('quantitative_value', 'qualitative_id')
    def get_success_value(self):
        for record in self:
            if record.question_type == 'quantitative' and \
                            record.quantitative_value >= record.q_from and \
                            record.quantitative_value <= record.q_to:
                record.is_success = True
            elif record.question_type == 'qualitative':
                if record.specification == record.qualitative_id.name:
                    record.is_success = True
