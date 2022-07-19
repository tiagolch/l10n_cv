# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2022-TODAY IEKINY Marcel (<iekinyfernandes@gmail.com>).
#
###############################################################################

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):

    _inherit = 'res.company'

    l10n_cv_efatura_send_invoice = fields.Boolean('Enviar Faturas para PE/DNRE')
    l10n_cv_efatura_send_invoice_next_execution_date = fields.Datetime(string="Próxima Execução")
    l10n_cv_efatura_led_code = fields.Char(string="Código",
                                           help="Código Local/Lógica de Emissão de Documentos Fiscais Eletrónicos (DFE).")
    l10n_cv_efatura_serie = fields.Char(string="Série",
                                        help="Código que o contribuinte utiliza para classificar a numeração dos DFE.")
    l10n_cv_efatura_address_detail = fields.Char(string="Detalhe de Endereço", size=100,
                                                 help="Detalhe de endereço do contribuinte emissor.")
    l10n_cv_efatura_address_code = fields.Char(string="Código de Endereço", size=20,
                                               help="Código de endereço em Cabo Verde com 6 níveis.")
    l10n_cv_efatura_iam_client_id = fields.Char(string="Client ID",
                                                help="Código de endereço em Cabo Verde com 6 níveis.")
    l10n_cv_efatura_iam_client_secret = fields.Char(string="Client Secret",
                                                    help="Código de endereço em Cabo Verde com 6 níveis.")

    @api.model
    def run_send_invoice(self):
        records = self.search([('l10n_cv_efatura_send_invoice_next_execution_date', '!=', False),
                               ('l10n_cv_efatura_send_invoice_next_execution_date', '<=', fields.Datetime.now())])
        if records:
            to_update = self.env['res.company']
            for record in records:
                record.l10n_cv_efatura_send_invoice_next_execution_date = datetime.now() + relativedelta(minutes=+15)
                to_update += record
            to_update._send_invoices()

    def _send_invoices(self):
        for rec in self:
            if not rec.l10n_cv_efatura_send_invoice:
                _logger.info('Enviar Faturas para PE/DNRE não está ativada.')
                continue
            invoices = self.env['account.move'].search([
                ('l10n_cv_efatura_is_einvoice', '=', True),
                ('state', 'not in', ['draft', 'cancel']),
                ('l10n_cv_efatura_pe_accepted', '=', False),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('company_id', '=', rec.id),
                ('l10n_cv_efatura_cron_count', '>', 1)]).sorted('invoice_date')
            if invoices:
                _logger.info("Enviar para PE/DNRE cerca de %d DFE(s)." % len(invoices))
            for invoice in invoices:
                try:
                    invoice.action_document_send()
                    if invoice.l10n_cv_efatura_pe_accepted:
                        invoice.l10n_cv_efatura_cron_count = 0
                    else:
                        invoice.l10n_cv_efatura_cron_count -= 1
                    self.env.cr.commit()
                except Exception:
                    self.env.cr.rollback()
                    invoice.l10n_cv_efatura_cron_count -= 1
                    self.env.cr.commit()
                    _logger.exception('Ocorreu um erro no envio do Documento Fiscal Eletrónico (IUD: %s).' % invoice.l10n_cv_efatura_iud)
