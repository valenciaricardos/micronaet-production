# -*- coding: utf-8 -*-
###############################################################################
#
# OpenERP, Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
import logging
import openerp
import xlsxwriter
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class SaleOrderProcurementReportWizard(orm.TransientModel):
    ''' Procurements depend on sale
    '''    
    _name = 'sale.order.procurement.report.wizard'
    _description = 'Sale produrement wizard'
    
    # -------------------------------------------------------------------------
    # Utilty:
    # -------------------------------------------------------------------------
    def extract_report_grouped_in_excel(
            self, cr, uid, data=None, context=None):
        ''' Extract XLSX mode for groupe report (used for frames)
        '''    
        # ---------------------------------------------------------------------
        # Utility:
        # ---------------------------------------------------------------------
        def write_xls_mrp_line(WS, row, line):
            ''' Write line in excel file
            '''
            col = 0
            for item, format_cell in line:
                WS.write(row, col, item, format_cell)
                col += 1
            return True

        # Create file:
        filename = '/tmp/production_status.xlsx'
        _logger.info('Start export status on %s' % filename)
        WB = xlsxwriter.Workbook(filename)
        WS = WB.add_worksheet(_('Frame'))

        # Format for cell:            
        num_format = '#,##0.00'
        format_title = WB.add_format({
            'bold': True, 
            'font_color': 'black',
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': 'gray',
            'border': 1,
            'text_wrap': True,
            })
        format_number = WB.add_format({
            'font_name': 'Arial',
            'font_size': 9,
            'align': 'right',
            'bg_color': 'white',
            'border': 1,
            'num_format': num_format,
            })
        
        # -----------------------------------------------------------------
        # Export excel report:        
        # -----------------------------------------------------------------
        # Write header:
        WS.set_row(0, 20) # Row height
        WS.set_column ('A:A', 35) # Col width
        
        header = [
            (_('Item'), format_title),
            (_('TODO'), format_title),
            (_('Done'), format_title),
            (_('Total'), format_title), 
            ]
        write_xls_mrp_line(WS, 0, header)
            
        # Write body:
        i = 1 # row position (before 0)
        
        
        
        WB.close()
        _logger.info('End generation framte status report %s' % filename)

        # Creaet attachment for return XLSX file as download:
        attachment_pool = self.pool.get('ir.attachment')
        b64 = open(filename, 'rb').read().encode('base64')
        attachment_id = attachment_pool.create(cr, uid, {
            'name': 'Frame MRP status',
            'datas_fname': 'frame_mrp_status.xlsx',
            'type': 'binary',
            'datas': b64,
            'partner_id': 1,
            'res_model':'res.partner',
            'res_id': 1,
            }, context=context)
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/saveas?model=ir.attachment&field=datas&'
                'filename_field=datas_fname&id=%s' % attachment_id,
            'target': 'self',
            }   
        
    # --------------
    # Button events:
    # --------------
    def print_report(self, cr, uid, ids, context=None):
        ''' Redirect to report passing parameters
        ''' 

        wiz_proxy = self.browse(cr, uid, ids)[0]
            
        datas = {}
        datas['wizard'] = True # started from wizard
        datas['xlsx'] = False
        
        if wiz_proxy.report_type == 'detailed':
            report_name = 'mx_procurement_report' 
        elif wiz_proxy.report_type == 'grouped': # grouped
            report_name = 'mx_procurement_grouped_report' 
        elif wiz_proxy.report_type == 'family':
            report_name = 'mx_procurement_grouped_family_report' # TODO change
        else: 
            datas['xlsx'] = True # frame XLS mode
               
        datas['from_date'] = wiz_proxy.from_date or False
        datas['to_date'] = wiz_proxy.to_date or False
        datas['from_deadline'] = wiz_proxy.from_deadline or False
        datas['to_deadline'] = wiz_proxy.to_deadline or False

        datas['family_id'] = wiz_proxy.family_id.id or False
        datas['family_name'] = wiz_proxy.family_id.name or ''
        
        datas['code_start'] = wiz_proxy.code_start
        datas['code_partial'] = wiz_proxy.code_partial
        
        datas['no_forecast'] = wiz_proxy.no_forecast
        datas['code_from'] = wiz_proxy.code_from

        datas['record_select'] = wiz_proxy.record_select
        
        if datas['xlsx']: # Export in XLSX file 
            return self.extract_report_grouped_in_excel(
                cr, uid, data=datas, context=context)
        else: # Normal report:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': datas,
                }                

    _columns = {
        'report_type': fields.selection([
            ('detailed', 'Order in detail'),
            ('grouped', 'Order grouped by frame'),
            ('frame', 'Frame for color (XLSX)'),
            ('family', 'Order family grouped'),
            ], 'Report type', required=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'family_id': fields.many2one('product.template', 'Family', 
            domain=[('is_family', '=', True)]),
            
        'no_forecast':fields.boolean('No forecast'),
        'record_select': fields.selection([
            ('all', 'Tutti'),
            ('mrp', 'Rimanenti da produrre'),
            ('delivery', 'Rimanenti da consegnare'),
            ], 'Selezione record', required=True),
            
        'from_date': fields.date('From', help='Date >='),
        'to_date': fields.date('To', help='Date <'),
        'from_deadline': fields.date('From deadline', help='Date deadline >='),
        'to_deadline': fields.date('To deadline', help='Date deadline <='),

        # Code filter:
        'code_start': fields.char('Code start', size=20), 
        'code_partial': fields.char('Code partial', size=20), 

        # Group option:        
        'code_from': fields.integer('Code from char'), 
        }
        
    _defaults = {
        'report_type': lambda *x: 'detailed',
        'no_forecast': lambda *x: True,
        'record_select': lambda *x: 'all',
        
        #'to_date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
