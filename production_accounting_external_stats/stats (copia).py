# -*- coding: utf-8 -*-
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
import os
import sys
from openerp import netsvc
import logging
from openerp.osv import osv, orm, fields
from datetime import datetime, timedelta
from openerp.tools.sql import drop_view_if_exists
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare)
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class MrpProductionStat(orm.Model):
    ''' Statistic data
    '''
    _name = 'mrp.production.stats'
    _description = 'MRP stats'
    _order = 'date'
    _rec_name = 'date'

    _columns = {
        'date': fields.date('Date', required=True),
        'total': fields.integer('Total', required=True), 
        'startup': fields.float('Start up time', digits=(16, 3)),     
        'mrp_id': fields.many2one(
            'mrp.production', 'Production', ondelete='cascade'),
        }

    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),    
        }

class MrpProductionStatMixed(osv.osv):
    ''' Create view object
    '''
    _name = 'mrp.production.stats.mixed'
    _description = 'MRP stats mixed'
    _order = 'workcenter_id,date_planned'
    _auto = False
    
    # Button event:
    def nothing(self, cr, uid, ids, context=None):
        ''' Dummy button
        '''
        return True

    _columns = {
        # mrp.production.workcenter.line:
        'name': fields.char('MRP name', readonly=True),
        'is_today': fields.boolean('Is today', readonly=True),
        'date_planned': fields.date('Date planned', readonly=True),
        'product_id': fields.many2one(
            'product.product', 'Family', readonly=True), 
        'production_id': fields.many2one(
            'mrp.production', 'Production', readonly=True), 
        'workcenter_id': fields.many2one(
            'mrp.workcenter', 'Line', readonly=True), 
        'lavoration_qty': fields.float('Lavoration q.', readonly=True),
        'hour': fields.float('Hour', readonly=True),
        'workers': fields.integer('Workers *', readonly=True),
        
        # sale.order.line:
        'todo_qty': fields.float('Total q.*', readonly=True),
        'maked_qty': fields.float('Done q.*', readonly=True),
        'remain_qty': fields.float('Remain q.*', readonly=True),
    
        #'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
        #                          ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month', readonly=True),
        #'type': fields.selection([('import', 'Import'), ('export', 'Export')], 'Type'),
        #'currency_id': fields.many2one('res.currency', "Currency", readonly=True),mrp.workers
        }
        
    def init(self, cr):
        drop_view_if_exists(cr, 'mrp_production_stats_mixed')
        cr.execute("""
            CREATE or REPLACE view mrp_production_stats_mixed as (
                SELECT 
                    wl.id as id,
                    wl.name as name,
                    wl.production_id as production_id,
                    wl.workcenter_id as workcenter_id,
                    wl.lavoration_qty as lavoration_qty,
                    wl.date_planned as date_planned,
                    DATE(wl.date_planned) = DATE(now()) as is_today,
                    wl.hour as hour,
                    
                    0 as workers,                    
                    mrp.product_id as product_id,
                    
                    sol.todo_qty as todo_qty,
                    sol.maked_qty as maked_qty,
                    (sol.todo_qty - sol.maked_qty) as remain_qty
                FROM
                    mrp_production_workcenter_line wl
                    LEFT JOIN 
                    (
                        SELECT 
                            mrp_id, 
                            sum(product_uom_qty) todo_qty,
                            sum(product_uom_maked_sync_qty) maked_qty
                        FROM sale_order_line
                        GROUP BY
                            mrp_id
                    ) sol
                    ON (wl.production_id = sol.mrp_id)

                    LEFT JOIN 
                    mrp_production mrp           
                    ON (wl.production_id = mrp.id)
                    
                    
                WHERE 
                    wl.state != 'cancel'
                )""")

class MrpProduction(orm.Model):
    ''' Statistic data
    '''
    _inherit = 'mrp.production'
    
    # Button events:
    def start_blocking_stats(self, cr, uid, ids, context=None):
        ''' Save current production to check difference
        '''
        blocked = sum([item.product_uom_maked_sync_qty for item in self.browse(
            cr, uid, ids, context=context)[0].order_line_ids])
        self.write(cr, uid, ids, {
            'stat_start_total': blocked,            
            }, context=context)
        return True
    
    def stop_blocking_stats(self, cr, uid, ids, context=None):
        ''' Save current production in log events
        '''
        blocked = sum([item.product_uom_maked_sync_qty for item in self.browse(
            cr, uid, ids, context=context)[0].order_line_ids])
        mrp_proxy = self.browse(cr, uid, ids, context=context)[0]    
        total = blocked - mrp_proxy.stat_start_total
        date = mrp_proxy.stat_start_date or datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT)
            
        # Create new stat record:
        self.pool.get('mrp.production.stats').create(cr, uid, {
            'date': date,
            'total': total,
            'startup': mrp_proxy.stat_startup,
            'mrp_id': ids[0],            
            }, context=context)
        return True    
    
    _columns = {
        'stat_start_date': fields.date('Ref. Date', 
            help='Ref. date for blocking operation'),
        'stat_start_total': fields.integer('Ref. Total',
            help='Total current item when start blocking operation'),
        'stat_startup': fields.float('Start up time', digits=(16, 3)),     
        'stats_ids': fields.one2many(
            'mrp.production.stats', 'mrp_id', 'Stats'), 
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
