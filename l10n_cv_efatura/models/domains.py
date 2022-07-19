# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2022-TODAY IEKINY Marcel (<iekinyfernandes@gmail.com>).
#
###############################################################################

from odoo import models, fields, api

class Domain(models.Model):

    _name = 'l10n_cv_efatura.domain'
    _description = 'Domains'

    active_ = fields.Boolean(string='Ativo', default=True)
    code = fields.Char(string='Código', size=4, index=True, required=True)
    name = fields.Char(string='Descrição', index=True, required=True)
    domain = fields.Char(string='Domínio', size=50, required=True)
