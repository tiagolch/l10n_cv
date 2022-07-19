# -*- coding: utf-8 -*-
###############################################################################
#
#    Marcel YEKINI
#    Copyright (C) 2022-TODAY Marcel YEKINI (<iekinyfernandes@gmail.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
{
    'name': 'Fatura Eletrónica - Cabo Verde',
    'version': '1.0',
    'summary': 'Cape-verdean Electronic Invoicing',
    "author": "MARCEL YEKINI",
    'support': 'iekinyfernandes@gmail.com',
    'sequence': -50,
    'description': """Cape-verdean Electronic Invoicing.""",
    'category': 'Localization',
    'website': '#',
    'live_test_url': '#',
    "development_status": "Beta",
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'wizard/account_move_wizard_view.xml',
        'views/settings_view.xml',
        'views/domains_view.xml',
        'views/res_company_view.xml',
        'views/account_move_view.xml',
        'views/account_payment_view.xml',
        'views/account_journal_view.xml',
        'report/report_invoice_document_inherit.xml',
        'report/report_payment_receipt_document_inherit.xml',
        'menus/menu.xml',
    ],
    'images': [],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
