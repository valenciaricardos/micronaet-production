###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    'name': 'Production BOM for working process',
    'version': '0.1',
    'category': '',
    'description': """
        Add extra information for manage BOM as a work BOM
        Add report for status of lines and workers per day
        """,
    'author': 'Micronaet S.r.l. - Nicola Riolini',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'sale',
        'mrp',
        'hr',
        'mrp',
        'mrp_operations',
        'working_bom',
        #'production_accounting_external',
        #'production_workhour', # Replaced with:
        'hr_workhour',
        #'report',
        'report_webkit', # TODO remove
        #'report_aeroo',
        #'report_aeroo_ooo',
        ],
    'init_xml': [],
    'demo': [],
    'data': [
        #'security/ir.model.access.csv',
        #'wizard/create_workcenter_view.xml',     
        'wizard/wizard_report_status_view.xml',
        'production_views.xml',

        'report/status_hour_report.xml',
        #'report/status_work_report.xml',
        #'report/status_hour_report.xml',
        #'report/status_work.xml',
        #'report/status_hour.xml',
        ],
    'active': False,
    'installable': True,
    'auto_install': False,
    }
