# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2022-TODAY IEKINY Marcel (<iekinyfernandes@gmail.com>).
#
###############################################################################

from odoo import api, fields, models, _

class AccountPayment(models.Model):

    _inherit = 'account.payment'

    l10n_cv_efatura_receipt_type_code = fields.Selection(selection=lambda self: self.l10n_cv_efatura_receipt_type_code_values(),
                                                     string='Tipo de Recibo', help='Código de Tipo de Recibo')
    l10n_cv_efatura_is_einvoice = fields.Boolean('Fatura Eletrónica', related="move_id.l10n_cv_efatura_is_einvoice")
    l10n_cv_efatura_pe_accepted = fields.Boolean('Aceitado por PE', related="move_id.l10n_cv_efatura_pe_accepted")
    l10n_cv_efatura_document_type = fields.Selection(selection=lambda self: self.l10n_cv_efatura_document_type_values(),
                                                     related="move_id.l10n_cv_efatura_document_type",
                                                     string='Tipo de Documento',
                                                     help='Tipo de Documento Fiscal Eletrónico')
    l10n_cv_efatura_repository_code = fields.Selection(selection=lambda self: self.l10n_cv_efatura_repository_code_values(),
        string='Repositório', related="move_id.l10n_cv_efatura_repository_code",
        help='Repositório de Armazenamento na base de dados.', copy=True)
    l10n_cv_efatura_iud = fields.Char(string='IUD', size=45, related="move_id.l10n_cv_efatura_iud",
                                      help="Identificador Único de DFE em Cabo Verde.")

    l10n_cv_efatura_transmission_issue_mode = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_transmission_issue_mode_values(),
        related="move_id.l10n_cv_efatura_transmission_issue_mode",
        string='Modo Transmissão',
        help='Modo de Transmissão', store=True)
    l10n_cv_efatura_reason_type_code = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_reason_type_code_values(),
        related="move_id.l10n_cv_efatura_reason_type_code",
        string='Motivo',
        help='Reason Type Code', store=True)
    l10n_cv_efatura_reason_description = fields.Text(string="Descrição", related="move_id.l10n_cv_efatura_reason_description", store=True)

    l10n_cv_efatura_xml = fields.Binary(string="XML File", related="move_id.l10n_cv_efatura_xml")
    l10n_cv_efatura_xml_filename = fields.Char(string="XML Filename", related="move_id.l10n_cv_efatura_xml_filename")


    # Default values
    @api.model
    def default_get(self, fields):
        res = super(AccountPayment, self).default_get(fields)
        res['l10n_cv_efatura_receipt_type_code'] = '3'
        res['l10n_cv_efatura_document_type'] = '4'
        res['l10n_cv_efatura_transmission_issue_mode'] = '1'
        return res

    # Callback Methods
    def l10n_cv_efatura_document_type_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search([('domain', '=', 'DOCUMENT_TYPE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_repository_code_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search([('domain', '=', 'REPOSITORY'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_transmission_issue_mode_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'TRANSMISSION_ISSUE_MODE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_reason_type_code_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'REASON_TYPE_CODE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_receipt_type_code_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'RECEIPT_TYPE_CODE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]


    # Onchange Methods
    @api.onchange('l10n_cv_efatura_transmission_issue_mode')
    def onchange_l10n_cv_efatura_transmission_issue_mode(self):
        for rec in self:
            rec.l10n_cv_efatura_reason_type_code = None
            rec.l10n_cv_efatura_reason_description = None

    @api.onchange('l10n_cv_efatura_reason_type_code')
    def onchange_l10n_cv_efatura_reason_type_code(self):
        for rec in self:
            rec.l10n_cv_efatura_reason_description = None

    # Overridden methods
    @api.model_create_multi
    def create(self, vals_list):
        payments = super(AccountPayment, self).create(vals_list)
        for pay in payments:
            move = self.env['account.move'].search([('name', '=', pay.move_id.ref),
                                                    ('l10n_cv_efatura_is_einvoice', '=', True),
                                                    ('l10n_cv_efatura_document_type', '=', '1')], limit=1)
            if move:
                pay.move_id.write({
                    'l10n_cv_efatura_is_einvoice': move.l10n_cv_efatura_pe_accepted,
                    'l10n_cv_efatura_transmission_issue_mode': move.l10n_cv_efatura_transmission_issue_mode,
                    'l10n_cv_efatura_repository_code': move.l10n_cv_efatura_repository_code,
                    'l10n_cv_efatura_document_type': '4'
                })
        return payments


    # Actions Methods
    def action_document_send(self):
        for rec in self:
            rec.move_id.l10n_cv_efatura_transmission_issue_mode = rec.l10n_cv_efatura_transmission_issue_mode
            rec.move_id.l10n_cv_efatura_reason_type_code = rec.l10n_cv_efatura_reason_type_code
            rec.move_id.l10n_cv_efatura_reason_description = rec.l10n_cv_efatura_reason_description
            rec.move_id.onchange_l10n_cv_efatura_is_einvoice()
            if not rec.move_id.l10n_cv_efatura_iud:
                rec.move_id._compute_l10n_cv_efatura_iud()
            rec.move_id.action_document_send()

    def action_cancel_move_efatura(self):
        view = self.env.ref('l10n_cv_efatura.view_account_move_wizard_form').read()[0]
        return {
            'name': _('Cancelar Documento Fiscal Eletrónico (DFE)'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': view['id'],
            'target': 'new',
            'res_id': self.move_id.id
        }
