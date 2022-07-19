# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2022-TODAY IEKINY Marcel (<iekinyfernandes@gmail.com>).
#
###############################################################################

from odoo import api, fields, models, _
from datetime import datetime, timedelta
import random
from odoo.exceptions import ValidationError, UserError
import xml.etree.ElementTree as ET
import base64
import requests
import json
import qrcode
import logging
from io import BytesIO

MIDDLEWARE_BASE_ENDPOINT = 'https://localhost:3443'
DFE_VIEW_URL = 'https://pe.efatura.cv/dfe/view'
MOVE_TYPE_DFE = {'out_invoice': '1', 'out_refund': '5', 'out_receipt': '4', 'entry': '4'}

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):

    _inherit = 'account.move'

    l10n_cv_efatura_issue_time = fields.Datetime(string='Issue Time', readonly=True, copy=False,
                                   states={'draft': [('readonly', False)]})

    l10n_cv_efatura_cancel_reason = fields.Text(string="Motivo Cancelamento", copy=False,
                                                help="Motivo de cancelamento do documento")
    l10n_cv_efatura_event_type_code = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_event_type_code_values(),
        string='Tipo de Evento',
        help='Tipo de Evento de Cancelamento ou de Inutilização', copy=False)
    l10n_cv_efatura_pe_accepted = fields.Boolean('Aceitado por PE', store=True, copy=False)
    l10n_cv_efatura_cron_count = fields.Integer('Cron count available', default=5, copy=False,
                                                help='Número de tentativas disponíveis para enviar a Fatura Eletrónica pela Cron Task')
    l10n_cv_efatura_is_einvoice = fields.Boolean('Fatura Eletrónica', copy=False)

    # e-Fatura fields
    l10n_cv_efatura_document_type = fields.Selection(selection=lambda self: self.l10n_cv_efatura_document_type_values(),
                                                     string='Tipo de Documento',
                                                     help='Tipo de Documento Fiscal Eletrónico')
    l10n_cv_efatura_iud = fields.Char(string='IUD', copy=False, size=45,
                                      help="Identificador Único de DFE em Cabo Verde.",
                                      compute='_compute_l10n_cv_efatura_iud', store=True, tracking=True)
    l10n_cv_efatura_country = fields.Char(string='País', default='CV', store=False)
    l10n_cv_efatura_repository_code = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_repository_code_values(),
        string='Repositório',
        help='Repositório de Armazenamento na base de dados.', copy=True)
    l10n_cv_efatura_serie = fields.Char(string='Série', size=10, copy=False,
                                        help='Código que o contribuinte utiliza para classificar a numeração dos DFE.')
    l10n_cv_efatura_document_number = fields.Char(string='Nº Documento', copy=False, size=9,
                                                  help='Número que identifica um Documento Fiscal Eletrónico.')
    l10n_cv_efatura_random_code = fields.Char('Random Code', size=10, copy=False, store=False)

    l10n_cv_efatura_amount_discount = fields.Monetary(string='Total Discount', store=True, readonly=True,
                                                      compute='_compute_discount', default=0)  # tracking=True
    l10n_cv_efatura_total_before_discount = fields.Monetary(string='Total Before Discount', store=True,
                                                            compute='_compute_total_before_discount')
    l10n_cv_efatura_charge_total_amount = fields.Monetary(string='Total de Linhas Encargo', store=True, readonly=True,
                                                      compute='_compute_l10n_cv_efatura_charge_total_amount', default=0)
    l10n_cv_efatura_price_extension_total_amount = fields.Monetary(string='Preço Total', store=True, readonly=True,
                                                      compute='_compute_l10n_cv_efatura_price_extension_total_amount', default=0)
    l10n_cv_efatura_net_total = fields.Monetary(string='Total Líquido', store=True, readonly=True,
                                                      compute='_compute_l10n_cv_efatura_net_total', default=0)
    l10n_cv_efatura_tax_total_amount = fields.Monetary(string='Total de Imposto', store=True, readonly=True,
                                                      compute='_compute_l10n_cv_efatura_tax_total_amount', default=0)
    l10n_cv_efatura_tax_total_amount = fields.Monetary(string='Total de Imposto', store=True, readonly=True,
                                                       compute='_compute_l10n_cv_efatura_tax_total_amount', default=0)
    l10n_cv_efatura_payable_amount = fields.Monetary(string='Total a Pagar', store=True, readonly=True,
                                                       compute='_compute_l10n_cv_efatura_payable_amount', default=0)
    l10n_cv_efatura_software_code = fields.Char(string="Código", size=50, readonly=True, copy=False)
    l10n_cv_efatura_transmitter_tax_id = fields.Char(string="Trasmitter TaxId", size=15, readonly=True, copy=False)
    l10n_cv_efatura_software_name = fields.Char(string="Nome", readonly=True, copy=False)
    l10n_cv_efatura_software_version = fields.Char(string="Versão", readonly=True, copy=False)

    l10n_cv_efatura_xml = fields.Binary(string="XML File", copy=False)
    l10n_cv_efatura_xml_filename = fields.Char(string="XML Filename", copy=False)
    l10n_cv_efatura_xml_event = fields.Text(string="XML Event", store=False, copy=False)
    l10n_cv_efatura_xml_event_filename = fields.Char(string="XML Event", store=False, copy=False)

    l10n_cv_efatura_transmission_issue_mode = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_transmission_issue_mode_values(),
        string='Modo Transmissão', help='Modo de Transmissão')
    l10n_cv_efatura_reason_type_code = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_reason_type_code_values(),
        string='Motivo', help='Reason Type Code')
    l10n_cv_efatura_reason_description = fields.Text(string="Descrição")
    l10n_cv_efatura_issue_reason_code = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_issue_reason_code_values(),
        string='Motivo Emissão',help='Motivo da Emissão')

    l10n_cv_efatura_receipt_type_code = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_receipt_type_code_values(),
        string='Tipo de Recibo', help='Código de Tipo de Recibo')

    l10n_cv_efatura_qr_code = fields.Binary(string="QR Code", attachment=True, store=True, copy=False)


    # Default values
    @api.model
    def default_get(self, fields):
        res = super(AccountMove, self).default_get(fields)
        res['l10n_cv_efatura_software_code'] = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_cv_efatura.software_code')
        res['l10n_cv_efatura_transmitter_tax_id'] = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_cv_efatura.transmitter_tax_id')
        res['l10n_cv_efatura_software_name'] = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_cv_efatura.software_name')
        res['l10n_cv_efatura_software_version'] = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_cv_efatura.software_version')
        return res

    # Callback Methods
    def l10n_cv_efatura_document_type_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search([('domain', '=', 'DOCUMENT_TYPE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_repository_code_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search([('domain', '=', 'REPOSITORY'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_event_type_code_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'EVENT_TYPE_CODE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_transmission_issue_mode_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'TRANSMISSION_ISSUE_MODE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_reason_type_code_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'REASON_TYPE_CODE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_issue_reason_code_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'ISSUE_REASON_CODE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_receipt_type_code_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'RECEIPT_TYPE_CODE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]


    # Compute Methods
    @api.depends('date', 'l10n_cv_efatura_is_einvoice', 'l10n_cv_efatura_repository_code',
                 'l10n_cv_efatura_document_type')
    def _compute_l10n_cv_efatura_iud(self):
        for rec in self:
            if not rec.l10n_cv_efatura_pe_accepted and rec.l10n_cv_efatura_is_einvoice and rec.date \
                    and rec.l10n_cv_efatura_repository_code and rec.l10n_cv_efatura_document_type and rec.l10n_cv_efatura_document_number \
                    and rec.company_id.vat and rec.company_id.l10n_cv_efatura_led_code:
                invoice_date = datetime.strptime(str(self.date), '%Y-%m-%d')
                invoice_year = str(invoice_date.year)[-2:]
                led = '{:05}'.format(int(rec.company_id.l10n_cv_efatura_led_code))
                random_code = random.sample([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 10)
                rec.l10n_cv_efatura_random_code = ''.join(str(e) for e in random_code)
                doc_type = '{:02}'.format(int(rec.l10n_cv_efatura_document_type))
                rec.l10n_cv_efatura_iud = '{}{}{:02d}{:02d}{}{}{}{}{}'.format(rec.l10n_cv_efatura_repository_code,
                                                                      invoice_year, invoice_date.month,
                                                                      invoice_date.day, rec.company_id.vat, led,
                                                                      doc_type,
                                                                      rec.l10n_cv_efatura_document_number,
                                                                      rec.l10n_cv_efatura_random_code)
                rec.l10n_cv_efatura_iud = 'CV' + rec.l10n_cv_efatura_iud + str(
                    AccountMove.luhn_check_digit(rec.l10n_cv_efatura_iud))

    @api.depends('invoice_line_ids.price_subtotal')
    def _compute_discount(self):
        for rec in self:
            discount = 0.0
            for line in rec.invoice_line_ids:
                discount += (AccountMove.exclude_tax(line.price_unit, line.tax_ids) * line.quantity * line.discount) / 100
            rec.l10n_cv_efatura_amount_discount = discount

    @api.depends('invoice_line_ids')
    def _compute_total_before_discount(self):
        total = 0
        for line in self.invoice_line_ids:
            total += line.price_unit * line.quantity
        self.l10n_cv_efatura_total_before_discount = total

    @api.depends('invoice_line_ids.quantity', 'invoice_line_ids.price_unit')
    def _compute_l10n_cv_efatura_price_extension_total_amount(self):
        for rec in self:
            total_price = 0.0
            for line in rec.invoice_line_ids:
                aux = line.quantity * AccountMove.exclude_tax(line.price_unit, line.tax_ids)
                if line.l10n_cv_efatura_product_line_type == 'N' or line.l10n_cv_efatura_product_line_type == 'C':
                    total_price += aux
                elif line.l10n_cv_efatura_product_line_type == 'D':
                    total_price -= aux
            rec.l10n_cv_efatura_price_extension_total_amount = total_price

    @api.depends('invoice_line_ids.price_total')
    def _compute_l10n_cv_efatura_net_total(self):
        for rec in self:
            net_total_amount = 0.0
            for line in rec.invoice_line_ids:
                if line.l10n_cv_efatura_product_line_type == 'N' or line.l10n_cv_efatura_product_line_type == 'C':
                    net_total_amount += line.price_subtotal
                elif line.l10n_cv_efatura_product_line_type == 'D':
                    net_total_amount -= line.price_subtotal
            rec.l10n_cv_efatura_net_total = net_total_amount

    @api.depends('invoice_line_ids.price_subtotal')
    def _compute_l10n_cv_efatura_charge_total_amount(self):
        for rec in self:
            charge_total_amount = 0.0
            for line in rec.invoice_line_ids:
                if line.l10n_cv_efatura_product_line_type == 'C':
                    charge_total_amount += line.quantity * AccountMove.exclude_tax(line.price_unit, line.tax_ids)
            rec.l10n_cv_efatura_charge_total_amount = charge_total_amount

    @api.depends('amount_by_group')
    def _compute_l10n_cv_efatura_tax_total_amount(self):
        for rec in self:
            tax_total_amount = 0.0
            for line in rec.invoice_line_ids:
                for tax in line.tax_ids:
                    line_tax_total_amount = line.price_subtotal * tax.amount / 100
                    if line.l10n_cv_efatura_product_line_type == 'N' or line.l10n_cv_efatura_product_line_type == 'C':
                        tax_total_amount += line_tax_total_amount
                    elif line.l10n_cv_efatura_product_line_type == 'D':
                        tax_total_amount -= line_tax_total_amount
            rec.l10n_cv_efatura_tax_total_amount = tax_total_amount

    @api.depends('l10n_cv_efatura_net_total', 'l10n_cv_efatura_tax_total_amount')
    def _compute_l10n_cv_efatura_payable_amount(self):
        for rec in self:
            rec.l10n_cv_efatura_payable_amount = rec.l10n_cv_efatura_net_total + rec.l10n_cv_efatura_tax_total_amount

    # Onchange Methods
    @api.onchange('l10n_cv_efatura_is_einvoice')
    def onchange_l10n_cv_efatura_is_einvoice(self):
        for rec in self:
            if rec.l10n_cv_efatura_is_einvoice:
                rec.l10n_cv_efatura_document_number = '{:09d}'.format(rec._origin.id)
                rec.l10n_cv_efatura_software_code = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.software_code')
                rec.l10n_cv_efatura_transmitter_tax_id = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.transmitter_tax_id')
                rec.l10n_cv_efatura_software_name = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.software_name')
                rec.l10n_cv_efatura_software_version = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.software_version')
                if not rec.l10n_cv_efatura_repository_code:
                    rec.l10n_cv_efatura_repository_code = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.repository_code')
                if not rec.l10n_cv_efatura_transmission_issue_mode:
                    rec.l10n_cv_efatura_transmission_issue_mode = '1'
                rec.l10n_cv_efatura_document_type = MOVE_TYPE_DFE[self.move_type]
                if rec.l10n_cv_efatura_document_type == '4':
                    rec.l10n_cv_efatura_receipt_type_code = '3'
                if rec.move_type == 'out_invoice' and rec.journal_id.l10n_cv_efatura_document_type:
                    rec.l10n_cv_efatura_document_type = rec.journal_id.l10n_cv_efatura_document_type


    @api.onchange('l10n_cv_efatura_transmission_issue_mode')
    def onchange_l10n_cv_efatura_transmission_issue_mode(self):
        for rec in self:
            rec.l10n_cv_efatura_reason_type_code = None
            rec.l10n_cv_efatura_reason_description = None

    @api.onchange('l10n_cv_efatura_reason_type_code')
    def onchange_l10n_cv_efatura_reason_type_code(self):
        for rec in self:
            rec.l10n_cv_efatura_reason_description = None


    # Actions Methods
    def action_cancel_move_efatura(self):
        for rec in self:
            if not rec.l10n_cv_efatura_pe_accepted:
                raise UserError(_('O Documento Fiscal Eletrónico (DFE) não pode ser cancelado.'))
            rec._validate_electronic_invoice()
            rec._validate_company_settings()
            rec._validate_software_transmissor_settings()
            rec._generate_event_xml()
            rec._send_event()
        return {'type': 'ir.actions.act_window_close'}

    def action_open_cancel_move_efatura(self):
        view = self.env.ref('l10n_cv_efatura.view_account_move_wizard_form').read()[0]
        return {
            'name': _('Cancelar Documento Fiscal Eletrónico (DFE)'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': view['id'],
            'target': 'new',
            'res_id': self.id,
        }

    def action_document_send(self):
        for rec in self:
            if rec.state == 'draft':
                continue
            rec._validate_electronic_invoice()
            rec._validate_company_settings()
            rec._validate_customer_settings()
            rec._validate_software_transmissor_settings()
            rec._generate_invoice_xml()
            rec._send_document()


    # Validation
    def _validate_electronic_invoice(self):
        self.ensure_one()
        if not self.l10n_cv_efatura_is_einvoice:
            raise UserError('Documento Fiscal Eletrónico (DFE) inválido.')
        if not self.l10n_cv_efatura_iud or len(self.l10n_cv_efatura_iud) != 45:
            raise UserError('Inválido IUD (Identificador Único de DFE). Favor verificar as configurações.')

    def _validate_company_settings(self):
        self.ensure_one()
        if not self.company_id.l10n_cv_efatura_send_invoice:
            raise UserError(
                'A empresa %s não está ativada para enviar Fatura Eletrónica. Favor verificar as configurações.' % self.company_id.name)
        if not self.company_id.l10n_cv_efatura_led_code or not self.company_id.l10n_cv_efatura_serie or not self.company_id.l10n_cv_efatura_address_code or not self.company_id.l10n_cv_efatura_address_detail:
            raise UserError(
                'Local de Emissão de DFEs não encontrado. Favor verificar as configurações da %s.' % self.company_id.name)
        if not self.company_id.l10n_cv_efatura_iam_client_id or not self.company_id.l10n_cv_efatura_iam_client_secret:
            raise UserError(
                'Client ID ou Client Secret não encontrado. Favor verificar as configurações da %s.' % self.company_id.name)

    def _validate_customer_settings(self):
        self.ensure_one()
        if not self.partner_id.phone and not self.partner_id.mobile and not self.partner_id.email:
            raise UserError(
                'O cliente %s deve ter pelo menos um dos contatos (telefone, móvel, email) definido.' % self.partner_id.name)

    def _validate_software_transmissor_settings(self):
        self.ensure_one()
        if not self.l10n_cv_efatura_software_code:
            raise UserError('Código do Software não encontrado. Favor verificar as configurações.')
        if not self.l10n_cv_efatura_transmitter_tax_id:
            raise UserError('Transmitter TaxId do Software não encontrado. Favor verificar as configurações.')
        if not self.l10n_cv_efatura_software_name:
            raise UserError('Nome do Software não encontrado. Favor verificar as configurações.')
        if not self.l10n_cv_efatura_software_version:
            raise UserError('Versão do Software não encontrado. Favor verificar as configurações.')
        if not self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.transmitter_key'):
            raise UserError('Transmitter Key não encontrado. Favor verificar as configurações.')


    # Electronic Invoicing Middleware Integration
    #
    # Envia o Documento Fiscal Eletrónico (DFE) para a Plataforma Eletrónica (PE)
    def _send_document(self):
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.middleware_base_endpoint')
        url = url + '/v1/dfe' if url else MIDDLEWARE_BASE_ENDPOINT + '/v1/dfe'
        headers = {
            'accept': 'application/json',
            'cv-ef-repository-code': self.l10n_cv_efatura_repository_code,
            'cv-ef-signature-type': 'internally-detached',
            'cv-ef-mw-core-transmitter-key': self.env['ir.config_parameter'].sudo().get_param(
                'l10n_cv_efatura.transmitter_key'),
            'cv-ef-iam-client-id': self.company_id.l10n_cv_efatura_iam_client_id,
            'cv-ef-iam-client-secret': self.company_id.l10n_cv_efatura_iam_client_secret
        }
        xml_decoded = base64.b64decode(self.l10n_cv_efatura_xml).decode('utf-8')
        file = {
            'file': (self.l10n_cv_efatura_iud + '.xml', xml_decoded)
        }
        _logger.info("Electronic Invoicing XML: {}".format(xml_decoded))
        try:
            r = requests.post(url, headers=headers, files=file, verify=False)
        except requests.exceptions.RequestException as e:
            raise UserError(e)
        else:
            if r.status_code == 200:
                data = json.loads(r.text)
                if not data or not data['responses']:
                    raise UserError('Ocorreu um erro. Favor tentar novamente! Se o erro persistir contatar o Administrador.')
                for response in data['responses']:
                    if response['succeeded']:
                        self.l10n_cv_efatura_pe_accepted = True
                        self._set_payment_as_electronic_invoice()
                        msg = 'O Documento Fiscal Eletrónico (DFE) foi criado e enviado com sucesso para Plataforma Eletrónica da DNRE (IUD: {}).'.format(
                            self.l10n_cv_efatura_iud)
                        xml_decoded = base64.b64decode(self.l10n_cv_efatura_xml).decode('utf-8')
                        attachments = [(self.l10n_cv_efatura_xml_filename, xml_decoded)]
                        self.message_post(body=msg, attachments=attachments)
                        break
                    else:
                        raise UserError(
                            '(' + response['messages'][0]['code'] + ') ' + response['messages'][0]['description'])
            else:
                raise UserError('(HTTP ERROR {}) {}'.format(r.status_code, r.text))

    # Cancelar Documento Fiscal Eletrónico (DFE)
    def _send_event(self):
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.middleware_base_endpoint')
        url = url + '/v1/event' if url else MIDDLEWARE_BASE_ENDPOINT + '/v1/event'
        headers = {
            'accept': 'application/json',
            'cv-ef-repository-code': self.l10n_cv_efatura_repository_code,
            'cv-ef-signature-type': 'internally-detached',
            'cv-ef-mw-core-transmitter-key': self.env['ir.config_parameter'].sudo().get_param(
                'l10n_cv_efatura.transmitter_key'),
            'cv-ef-iam-client-id': self.company_id.l10n_cv_efatura_iam_client_id,
            'cv-ef-iam-client-secret': self.company_id.l10n_cv_efatura_iam_client_secret
        }
        file = {
            'file': (self.l10n_cv_efatura_xml_event_filename, self.l10n_cv_efatura_xml_event)
        }
        try:
            r = requests.post(url, headers=headers, files=file, verify=False)
        except requests.exceptions.RequestException as e:
            raise UserError(e)
        else:
            if r.status_code == 200:
                data = json.loads(r.text)
                if not data or not data['responses']:
                    raise UserError('Ocorreu um erro. Favor tentar novamente! Se o erro persistir contatar o Administrador.')
                for response in data['responses']:
                    if response['succeeded']:
                        self.l10n_cv_efatura_pe_accepted = False
                        self.l10n_cv_efatura_cron_count = 0
                        msg = 'O Documento Fiscal Eletrónico (DFE) foi cancelado com sucesso pela Plataforma Eletrónica (IUD: {}).'.format(
                            self.l10n_cv_efatura_iud)
                        attachments = [(self.l10n_cv_efatura_xml_event_filename, self.l10n_cv_efatura_xml_event)]
                        self.message_post(body=msg, attachments=attachments)
                        break
                    else:
                        raise UserError(
                            '(' + response['messages'][0]['code'] + ') ' + response['messages'][0]['description'])
            else:
                raise UserError('(HTTP ERROR {}) {}'.format(r.status_code, r.text))


    # Generate DFE XML
    def _generate_invoice_xml(self):
        self.ensure_one()
        # Dfe is the root element
        dfe = ET.Element('Dfe', xmlns='urn:cv:efatura:xsd:v1.0', Version='1.0', Id=self.l10n_cv_efatura_iud,
                         DocumentTypeCode=self.l10n_cv_efatura_document_type)
        # Type of DFE
        invoice = self._build_invoice_node(dfe)
        # Identificação do DFE
        self._build_dfe_identification_xml(invoice)
        # Issue Reason
        self._build_issue_reason_xml(invoice)
        # Emissor (AccountingSupplierParty)
        self._build_emitter_party_xml(invoice)
        # Receptor/Destinatário (AccountingCustomerParty)
        self._build_receiver_party_xml(invoice)
        # Products and Services
        self._build_product_service_xml(invoice)
        # Totais
        self._build_totals_xml(invoice)
        # Pagamento

        # Entrega

        # Receipt Type Code
        self._build_receipt_type_code_xml(invoice)

        # References
        self._build_references_xml(invoice)

        # Nota
        if self.narration:
            ET.SubElement(invoice, 'Note').text = self.narration
        # Transmitter
        self._build_transmitter_xml(dfe)
        # Repository Code
        ET.SubElement(dfe, 'RepositoryCode').text = self.l10n_cv_efatura_repository_code
        aux = ET.tostring(dfe, encoding='utf-8', method='xml').decode('utf-8')
        if '<?xml ' not in aux:
            aux = '<?xml version="1.0" encoding="UTF-8"?>' + aux
        self.l10n_cv_efatura_xml = base64.b64encode(bytes(aux, encoding='utf-8'))
        self.l10n_cv_efatura_xml_filename = self.name.replace('/', '_') + '_efatura.xml'

    # Generate Event XML
    def _generate_event_xml(self):
        self.ensure_one()
        # Event is the root element
        date = fields.Datetime.context_timestamp(self, datetime.now())
        id = 'CV{}{}{}{}{}{}{}{}'.format(self.l10n_cv_efatura_repository_code, str(date.year)[-2:],
                                         '{:02}'.format(date.month), '{:02}'.format(date.day),
                                         '{:02}'.format(date.hour), '{:02}'.format(date.minute),
                                         '{:02}'.format(date.second), self.company_id.vat)
        event = ET.Element('Event', xmlns='urn:cv:efatura:xsd:v1.0', Version='1.0', Id=id,
                           EventTypeCode=self.l10n_cv_efatura_event_type_code)
        # event.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        # event.set('xsi:schemaLocation', 'urn:cv:efatura:xsd:v1.0 EnvelopedSignature.xsd')
        ET.SubElement(event, 'EmitterTaxId', CountryCode="CV").text = self.company_id.vat
        ET.SubElement(event, 'IssueDateTime').text = date.strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(event, 'IssueReasonDescription').text = self.l10n_cv_efatura_cancel_reason
        if self.l10n_cv_efatura_event_type_code == 'FDC':
            ET.SubElement(event, 'IUD').text = self.l10n_cv_efatura_iud
        else:
            ET.SubElement(event, 'LedCode').text = self.company_id.l10n_cv_efatura_led_code
            ET.SubElement(event, 'Serie').text = self.company_id.l10n_cv_efatura_serie
            ET.SubElement(event, 'DocumentTypeCode').text = self.l10n_cv_efatura_document_type
            ET.SubElement(event, 'DocumentNumberStart').text = '1'
            ET.SubElement(event, 'DocumentNumberEnd').text = '10'
        # Transmitter
        self._build_transmitter_xml(event, True)
        # Repository Code
        ET.SubElement(event, 'RepositoryCode').text = self.l10n_cv_efatura_repository_code
        self.l10n_cv_efatura_xml_event = ET.tostring(event, encoding='utf-8', method='xml').decode('utf-8')
        if '<?xml ' not in self.l10n_cv_efatura_xml_event:
            self.l10n_cv_efatura_xml_event = '<?xml version="1.0" encoding="UTF-8"?>' + self.l10n_cv_efatura_xml_event
        self.l10n_cv_efatura_xml_event_filename = id + '.xml'

    def _build_invoice_node(self, dfe):
        self.ensure_one()
        node_names = {'1': 'Invoice', '2': 'InvoiceReceipt', '3': 'SalesReceipt', '5': 'CreditNote', '4': 'Receipt'}
        return ET.SubElement(dfe, node_names.get(self.l10n_cv_efatura_document_type))

    def _build_dfe_identification_xml(self, invoice):
        self.ensure_one()
        ET.SubElement(invoice, 'LedCode').text = self.company_id.l10n_cv_efatura_led_code
        ET.SubElement(invoice, 'Serie').text = self.company_id.l10n_cv_efatura_serie
        ET.SubElement(invoice, 'DocumentNumber').text = str(int(self.l10n_cv_efatura_document_number))
        ET.SubElement(invoice, 'IssueDate').text = str(self.date)

        current_date_time = fields.Datetime.context_timestamp(self, datetime.now())
        if not self.l10n_cv_efatura_issue_time:
            self.l10n_cv_efatura_issue_time = fields.datetime.now()
        aux = datetime.strptime(current_date_time.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S') # Remove Timezone
        diff = aux - self.l10n_cv_efatura_issue_time
        diff_in_hours = diff.total_seconds() / 3600
        if diff_in_hours > 1:
            ET.SubElement(invoice, 'IssueTime').text = self.l10n_cv_efatura_issue_time.strftime("%H:%M:%S")
        else:
            ET.SubElement(invoice, 'IssueTime').text = current_date_time.time().strftime("%H:%M:%S")

        if self.invoice_date_due and self.l10n_cv_efatura_document_type == '1':
            ET.SubElement(invoice, 'DueDate').text = str(self.invoice_date_due)
        if self.l10n_cv_efatura_document_type in ['1', '2']:
            order_reference = ET.SubElement(invoice, 'OrderReference')
            ET.SubElement(order_reference, 'Id').text = self.name
            ET.SubElement(invoice, 'TaxPointDate').text = str(self.date)

    def _build_emitter_party_xml(self, invoice):
        self.ensure_one()
        emitter_party = ET.SubElement(invoice, 'EmitterParty')
        ET.SubElement(emitter_party, 'TaxId', CountryCode='CV').text = self.company_id.vat
        ET.SubElement(emitter_party, 'Name').text = self.company_id.name
        emitter_address = ET.SubElement(emitter_party, 'Address', CountryCode='CV')
        ET.SubElement(emitter_address, 'AddressDetail').text = self.company_id.l10n_cv_efatura_address_detail
        ET.SubElement(emitter_address, 'AddressCode').text = self.company_id.l10n_cv_efatura_address_code
        emitter_contacts = ET.SubElement(emitter_party, 'Contacts')
        if self.company_id.phone:
            ET.SubElement(emitter_contacts, 'Telephone').text = self.company_id.phone
        if self.company_id.email:
            ET.SubElement(emitter_contacts, 'Email').text = self.company_id.email
        if self.company_id.website:
            ET.SubElement(emitter_contacts, 'Website').text = self.company_id.website

    def _build_receiver_party_xml(self, invoice):
        self.ensure_one()
        if self.l10n_cv_efatura_document_type != '3':
            receiver_party = ET.SubElement(invoice, 'ReceiverParty')
            ET.SubElement(receiver_party, 'TaxId', CountryCode='CV').text = self.partner_id.vat
            ET.SubElement(receiver_party, 'Name').text = self.partner_id.name
            emitter_address = ET.SubElement(receiver_party, 'Address', CountryCode='CV')
            address_detail = ''
            if self.partner_id.country_id:
                address_detail += self.partner_id.country_id.name
            if self.partner_id.state_id:
                address_detail += ' - ' + self.partner_id.state_id.name
            if self.partner_id.city:
                address_detail += ' - ' + self.partner_id.city
            if self.partner_id.street:
                address_detail += ' - ' + self.partner_id.street
            ET.SubElement(emitter_address, 'AddressDetail').text = address_detail
            emitter_contacts = ET.SubElement(receiver_party, 'Contacts')
            if self.company_id.phone:
                ET.SubElement(emitter_contacts, 'Telephone').text = self.company_id.phone
            if self.company_id.email:
                ET.SubElement(emitter_contacts, 'Email').text = self.company_id.email
            if self.company_id.website:
                ET.SubElement(emitter_contacts, 'Website').text = self.company_id.website

    def _build_product_service_xml(self, invoice):
        self.ensure_one()
        if self.l10n_cv_efatura_document_type == '4':
            return
        lines = ET.SubElement(invoice, 'Lines')
        for move_line in self.invoice_line_ids:
            line = ET.SubElement(lines, 'Line', LineTypeCode=move_line.l10n_cv_efatura_product_line_type)
            ET.SubElement(line, 'Id').text = str(move_line.id)
            ET.SubElement(line, 'Quantity', UnitCode=move_line.l10n_cv_efatura_unidade, IsStandardUnitCode="true").text = AccountMove.format_number(move_line.quantity)
            price_unit = AccountMove.exclude_tax(move_line.price_unit, move_line.tax_ids)
            ET.SubElement(line, 'Price').text = AccountMove.format_number(price_unit)
            ET.SubElement(line, 'PriceExtension').text = AccountMove.format_number(move_line.quantity * price_unit)
            ET.SubElement(line, 'Discount', ValueType="P").text = AccountMove.format_number(move_line.discount)
            ET.SubElement(line, 'NetTotal').text = AccountMove.format_number(move_line.price_subtotal)
            line_tax = ET.SubElement(line, 'Tax')
            if move_line.tax_ids.name:
                if 'Tax' in move_line.tax_ids.name or 'IVA' in move_line.tax_ids.name:
                    line_tax.set('TaxTypeCode', "IVA")
                elif 'IS' in move_line.tax_ids.name:
                    line_tax.set('TaxTypeCode', "IS")
                elif 'TEU' in move_line.tax_ids.name:
                    line_tax.set('TaxTypeCode', "TEU")
                elif 'IR' in move_line.tax_ids.name:
                    line_tax.set('TaxTypeCode', "IR")
                else:
                    line_tax.set('TaxTypeCode', "IVA") #
                ET.SubElement(line_tax, 'TaxPercentage').text = AccountMove.format_number(move_line.tax_ids.amount)
            else:
                line_tax.set('TaxTypeCode', "NA")
                ET.SubElement(line_tax, 'TaxExemptionReasonCode').text = '1'
            line_item = ET.SubElement(line, 'Item')
            ET.SubElement(line_item, 'Description').text = move_line.product_id.name
            ET.SubElement(line_item,
                          'EmitterIdentification').text = move_line.product_id.barcode if move_line.product_id.barcode else move_line.product_id.default_code if move_line.product_id.default_code else str(move_line.product_id.id)
            ET.SubElement(line_item, 'HazardousRiskIndicator').text = 'false'

    def _build_totals_xml(self, invoice):
        self.ensure_one()
        if self.l10n_cv_efatura_document_type == '4':
            return
        totals = ET.SubElement(invoice, 'Totals')
        ET.SubElement(totals, 'PriceExtensionTotalAmount').text = AccountMove.format_number(self.l10n_cv_efatura_price_extension_total_amount)
        ET.SubElement(totals, 'ChargeTotalAmount').text = AccountMove.format_number(self.l10n_cv_efatura_charge_total_amount)
        ET.SubElement(totals, 'DiscountTotalAmount').text = AccountMove.format_number(self.l10n_cv_efatura_amount_discount)
        ET.SubElement(totals, 'NetTotalAmount').text = AccountMove.format_number(self.l10n_cv_efatura_net_total)
        ET.SubElement(totals, 'TaxTotalAmount').text = AccountMove.format_number(self.l10n_cv_efatura_tax_total_amount)
        ET.SubElement(totals, 'PayableAmount').text = AccountMove.format_number(self.l10n_cv_efatura_payable_amount)

    def _build_references_xml(self, invoice):
        self.ensure_one()
        if self.l10n_cv_efatura_document_type == '5' and self.reversed_entry_id:
            references = ET.SubElement(invoice, 'References')
            reference = ET.SubElement(references, 'Reference')
            ET.SubElement(reference, 'FiscalDocument', IsOldDocument='false').text = self.reversed_entry_id.l10n_cv_efatura_iud
        if self.l10n_cv_efatura_document_type == '4':
            ref_account_move = self.env['account.move'].search([('name', '=', self.ref)], limit=1)
            if ref_account_move:
                references = ET.SubElement(invoice, 'References')
                reference = ET.SubElement(references, 'Reference')
                ET.SubElement(reference, 'FiscalDocument', IsOldDocument='false').text = self.l10n_cv_efatura_iud
                ET.SubElement(reference, 'PaymentAmount').text = AccountMove.format_number(self.payment_id.amount)

    def _build_receipt_type_code_xml(self, invoice):
        self.ensure_one()
        if self.l10n_cv_efatura_document_type == '4':
            ET.SubElement(invoice, 'ReceiptTypeCode').text = self.l10n_cv_efatura_receipt_type_code

    def _build_issue_reason_xml(self, invoice):
        self.ensure_one()
        if self.l10n_cv_efatura_document_type == '5':
            ET.SubElement(invoice, 'IssueReasonCode').text = self.l10n_cv_efatura_issue_reason_code

    def _build_transmitter_xml(self, dfe, is_event=False):
        self.ensure_one()
        transmission = ET.SubElement(dfe, 'Transmission')
        ET.SubElement(transmission, 'IssueMode').text = '1' if is_event else str(self.l10n_cv_efatura_transmission_issue_mode)
        ET.SubElement(transmission, 'TransmitterTaxId', CountryCode='CV').text = self.l10n_cv_efatura_transmitter_tax_id
        software = ET.SubElement(transmission, 'Software')
        ET.SubElement(software, 'Code').text = self.l10n_cv_efatura_software_code
        ET.SubElement(software, 'Name').text = self.l10n_cv_efatura_software_name
        ET.SubElement(software, 'Version').text = self.l10n_cv_efatura_software_version
        if not is_event and self.l10n_cv_efatura_transmission_issue_mode == '2':
            current_date_time = fields.Datetime.context_timestamp(self, datetime.now())
            contingency = ET.SubElement(transmission, 'Contingency')
            ET.SubElement(contingency, 'LedCode').text = self.company_id.l10n_cv_efatura_led_code
            ET.SubElement(contingency, 'IssueDate').text = current_date_time.date().strftime("%Y-%m-%d")
            ET.SubElement(contingency, 'IssueTime').text = current_date_time.time().strftime("%H:%M:%S")
            ET.SubElement(contingency, 'ReasonTypeCode').text = self.l10n_cv_efatura_reason_type_code
            if self.l10n_cv_efatura_reason_type_code == '0':
                ET.SubElement(contingency, 'ReasonDescription').text = self.l10n_cv_efatura_reason_description

    # Override Methods
    def action_post(self):
        for move in self:
            move.prepare_electronic_invoice()
        super(AccountMove, self).action_post()

    def _set_payment_as_electronic_invoice(self):
        self.ensure_one()
        if self.l10n_cv_efatura_document_type == '1':
            move_payment = self.env['account.move'].search([('ref', '=', self.name), ('payment_id', '!=', False)], limit=1)
            if move_payment:
                move_payment.write({'l10n_cv_efatura_is_einvoice': True})

    def prepare_electronic_invoice(self):
        self.ensure_one()
        if self.company_id.l10n_cv_efatura_send_invoice:
            if not self.l10n_cv_efatura_is_einvoice and self.move_type in ['out_invoice', 'out_refund']:
                self.l10n_cv_efatura_is_einvoice = True
                self.onchange_l10n_cv_efatura_is_einvoice()
            self.l10n_cv_efatura_cron_count = 5
            self.l10n_cv_efatura_issue_time = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()),
                                                                '%Y-%m-%d %H:%M:%S')

    # QRCode Generator
    def generate_qr_code(self):
        data = '{}/{}'.format(DFE_VIEW_URL, self.l10n_cv_efatura_iud)
        qr_code = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10,
                                border=4, )
        qr_code.add_data(data)
        qr_code.make(fit=True)
        temp = BytesIO()
        qr_code.make_image().save(temp, format="PNG")
        self.l10n_cv_efatura_qr_code = base64.b64encode(temp.getvalue())

    # Luhn Algorithm - Check Digit
    def check_luhn(n):
        r = [int(ch) for ch in str(n)]
        return (sum(r[0::2]) + sum(sum(divmod(d * 2, 10)) for d in r[1::2])) % 10 == 0

    def luhn_check_digit(n):
        r = [int(ch) for ch in str(n)]
        soma = (sum(r[0::2]) + sum(sum(divmod(d * 2, 10)) for d in r[1::2]))
        return (soma * 9) % 10

    def format_number(n):
        n = float(n)
        if n.is_integer():
            return '{:d}'.format(int(n))
        result = '{:.2f}'.format(n)
        if result[-1] == '0':
            return result.rstrip(result[-1])
        return result

    def exclude_tax(price, tax_ids):
        for tax in tax_ids:
            price = price / (1 + tax.amount / 100)
        return price


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    l10n_cv_efatura_product_line_type = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_product_line_type_values(), string='Tipo de Linha',
        help='Tipo de Linha')

    l10n_cv_efatura_unidade = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_unidade_values(), string='Unidade',
        help='Tipo de Linha')

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveLine, self).default_get(fields)
        res['l10n_cv_efatura_product_line_type'] = 'N'
        res['l10n_cv_efatura_unidade'] = 'EA'
        return res

    # Callback Methods
    def l10n_cv_efatura_product_line_type_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'PRODUCT_LINE_TYPE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def l10n_cv_efatura_unidade_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search(
            [('domain', '=', 'UNIDADE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]
