# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2022-TODAY IEKINY Marcel (<iekinyfernandes@gmail.com>).
#
###############################################################################

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
import requests


class EInvoicingSettings(models.TransientModel):

    _inherit = "res.config.settings"

    transmitter_key = fields.Char(string="Transmitter Key",
                                  help="Chave única do transmissor para operações entre a aplicação cliente e o middleware.")
    transmitter_tax_id = fields.Char(string="TaxId", size=15)
    software_code = fields.Char(string="Código", size=50)
    software_name = fields.Char(string="Nome")
    software_version = fields.Char(string="Versão")
    repository_code = fields.Selection(
        selection=lambda self: self.l10n_cv_efatura_repository_code_values(),
        string='Repositório',
        help='Repositório de Armazenamento na Base de Dados.')
    middleware_base_endpoint = fields.Char(string="Base URL")

    # Callback Methods
    def l10n_cv_efatura_repository_code_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search([('domain', '=', 'REPOSITORY'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]

    def set_values(self):
        res = super(EInvoicingSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('l10n_cv_efatura.transmitter_key', self.transmitter_key)
        self.env['ir.config_parameter'].set_param('l10n_cv_efatura.software_code', self.software_code)
        self.env['ir.config_parameter'].set_param('l10n_cv_efatura.software_name', self.software_name)
        self.env['ir.config_parameter'].set_param('l10n_cv_efatura.software_version', self.software_version)
        self.env['ir.config_parameter'].set_param('l10n_cv_efatura.repository_code', self.repository_code)
        self.env['ir.config_parameter'].set_param('l10n_cv_efatura.transmitter_tax_id', self.transmitter_tax_id)
        self.env['ir.config_parameter'].set_param('l10n_cv_efatura.middleware_base_endpoint', self.middleware_base_endpoint)
        return res

    @api.model
    def get_values(self):
        res = super(EInvoicingSettings, self).get_values()
        transmitter_key = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.transmitter_key')
        middleware_base_endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.middleware_base_endpoint')
        software_code = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.software_code')
        transmitter_tax_id = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.transmitter_tax_id')
        software_name = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.software_name')
        software_version = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.software_version')
        repository_code = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.repository_code')
        repository_code = '1' if not repository_code else repository_code
        res.update(transmitter_key=transmitter_key,
                   middleware_base_endpoint=middleware_base_endpoint,
                   software_code=software_code,
                   software_name=software_name,
                   software_version=software_version,
                   repository_code=repository_code,
                   transmitter_tax_id=transmitter_tax_id)
        return res

    def action_transmitter_key(self):
        url = self.env['ir.config_parameter'].sudo().get_param('l10n_cv_efatura.middleware_base_endpoint')
        if not url:
            raise UserError('Base URL não pode ser vazio.')
        url += '/v1/core/transmitter-key'
        headers = {'accept': 'text/plain'}
        try:
            r = requests.get(url, headers=headers, verify=False)
        except requests.exceptions.RequestException as e:
            raise UserError(e)
        if r.status_code == 200:
            self.env['ir.config_parameter'].set_param('l10n_cv_efatura.transmitter_key', r.text)
