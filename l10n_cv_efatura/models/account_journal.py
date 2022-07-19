# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2022-TODAY IEKINY Marcel (<iekinyfernandes@gmail.com>).
#
###############################################################################

from odoo import api, fields, models, _


class AccountJournal(models.Model):

    _inherit = "account.journal"

    l10n_cv_efatura_document_type = fields.Selection(selection=lambda self: self.l10n_cv_efatura_document_type_values(),
                                                     string='Tipo de Documento',
                                                     help='Tipo de Documento Fiscal Eletrónico')

    # Callback Methods
    def l10n_cv_efatura_document_type_values(self):
        domains = self.env['l10n_cv_efatura.domain'].search([('domain', '=', 'DOCUMENT_TYPE'), ('active_', '=', True)])
        return [(domain.code, domain.name) for domain in domains]
