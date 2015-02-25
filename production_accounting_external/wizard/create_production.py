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

# Generic function 
def get_product_from_template(self, cr, uid, tmpl_id, context=None):
    ''' Return product (first) with that template ID
    '''
    product_ids = self.pool.get('product.product').search(cr, uid, [
        ('product_tmpl_id', '=', tmpl_id)
        ], context=context)
    if product_ids:
        return product_ids[0]
    else:
        return False
            
def return_view(self, cr, uid, res_id, view_name, object_name, context=None):
    '''Function that return dict action for next step of the wizard
    '''
    
    if not view_name: 
        return {'type': 'ir.actions.act_window_close'}

    view_element = view_name.split(".")
    views = []
    
    if len(view_element)!= 2: 
        return {'type': 'ir.actions.act_window_close'}

    model_id = self.pool.get('ir.model.data').search(
        cr, uid, [
            ('model', '=', 'ir.ui.view'), 
            ('module','=',view_element[0]), 
            ('name', '=', view_element[1]),
            ], context=context)
            
    if model_id:
        view_id = self.pool.get('ir.model.data').read(
            cr, uid, model_id)[0]['res_id']
        views = [(view_id, 'form'), (False, 'tree'), ]

    return {
        'view_type': 'form',
        'view_mode': 'form,tree',
        'res_model': object_name, # object linked to the view
        'views': views,
        'domain': [('id', 'in', res_id)], 
        #'views': [(view_id, 'form')],
        #'view_id': False,
        'type': 'ir.actions.act_window',
        #'target': 'new',
        'res_id': res_id,  # IDs selected
       }

class CreateMrpProductionWizard(orm.TransientModel):
    ''' Wizard that create a production order based on selected order lines
    '''
    
    _name = "mrp.production.create.wizard"
    
    # ---------------
    # Utility funtion
    # ---------------
    def preserve_window(self, cr, uid, ids, context=None):
        ''' Create action for return the same open wizard window
        '''
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[
            ('model', '=', 'mrp.production.create.wizard'),
            ('name','=','Create production order') # TODO needed?
            ], context=context)
        
        return {
            'type': 'ir.actions.act_window',
            'name': "Wizard create production order",
            'res_model': 'mrp.production.create.wizard',
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'nodestroy': True,
            }
        
    # ----------    
    # On Change:            
    # ----------    
    def onchange_append_production(self, cr, uid, ids, production_id, oc_total, 
            context=None):
        ''' Search values for total
        ''' 
        if not production_id:
            return {}

        res = {'value': {}}
        production_pool = self.pool.get('mrp.production')
        production_proxy = production_pool.browse(
            cr, uid, production_id, context=context)
        res['value']['current_total'] = production_proxy.product_qty
        res['value']['current_extra'] = production_proxy.extra_qty        
        res['value']['total'] = (
            production_proxy.product_qty or 0.0) + ( # production total
            #production_proxy.extra_qty or 0.0) + ( # production extra
            oc_total or 0.0) # current OC        
        return res 
           
    # --------------
    # Wizard button:
    # --------------
    def action_create_mrp_production_order(self, cr, uid, ids, context=None):
        ''' Create production order based on product_tmpl_id depend on quantity
            Redirect mrp.production form after
        '''        
        if context is None:
           context = {}

        wizard_browse = self.browse(cr, uid, ids, context=context)[0]

        # Create a production order and open it:
        production_pool = self.pool.get("mrp.production")
        
        product_id = get_product_from_template( # TODO use product_id?
            self, cr, uid, wizard_browse.product_tmpl_id.id, context=context)

        if wizard_browse.operation == 'create':
            p_id = production_pool.create(               
                cr, uid, {
                    'name': self.pool.get(
                        'ir.sequence').get(cr, uid, 'mrp.production'),
                    'product_id': product_id,
                    'product_qty': wizard_browse.total,
                    'product_uom': wizard_browse.product_id.uom_id.id,
                    'date_planned': wizard_browse.from_deadline,
                    'bom_id': wizard_browse.bom_id.id,
                    'user_id': uid,
                    'order_line_ids': [(6, 0, context.get("active_ids", []))],
                    }, context=context)
        else: # append
            p_id = wizard_browse.production_id.id
            self.pool.get('sale.order.line').write(
                cr, uid, context.get("active_ids", []), {
                    'mrp_id': p_id,
                    }, context=context)
            #production_pool.write(
            #    cr, uid, [p_id], {
            #        'order_line_ids': [(6, 0, context.get("active_ids", []))],
            #        }, context=context)

        # Load element from BOM: # TODO 
        #production_pool._action_load_materials_from_bom(
        #    cr, uid, p_id, context=context)    
        return return_view(
            self, cr, uid, p_id, 
            "mrp.mrp_production_form_view", 
            "mrp.production", context=context) 

    # -----------------
    # Default function:        
    # -----------------
    def default_oc_list(self, cr, uid, field, context=None):
        ''' Get list of order for confirm as default
            context: used for select product or family (grouping clause)
        '''
        
        if context is None:
            context = {}

        sol_pool = self.pool.get('sale.order.line')
        ids = sol_pool.search(cr, uid, [
            ('id', 'in', context.get("active_ids", [])),
            ], context=context)
        sol_browse = sol_pool.browse(cr, uid, ids, context=context) 
        
        if context.get('grouping', 'product') == 'product':
            ref_field = 'product_id'
        else:
            ref_field = 'family_id'    

        default = {
            "list": _("""
                <style>
                    .table_bf {
                         border: 1px solid black;
                         padding: 3px;
                     }
                    .table_bf td {
                         border: 1px solid black;
                         padding: 3px;
                         text-align: center;
                     }
                    .table_bf th {
                         border: 1px solid black;
                         padding: 3px;
                         text-align: center;
                         background-color: grey;
                         color: white;
                     }
                </style>
                <table class='table_bf'>
                <tr class='table_bf'>
                    <th>OC</th>
                    <th>Q.</th>
                    <th>Deadline</th>
                </tr>"""), 
            "is_error": False, 
            "oc_total": 0.0, 
            "total": 0.0, 
            "product": False, 
            "from_deadline": False, 
            "to_deadline": False, 
            "bom": False,
            "error": "", #TODO
            "warning": "", #TODO
            }             
        res = default.get(field, False)        
        old_product_id = False     
        
        try:
            if field == "template": # so template
                if ref_field == 'product_id':
                    return sol_browse[0].product_id.product_tmpl_id.id
                else: # family
                    return sol_browse[0].family_id.id                
        except:
            return False
        try:
            if field == "product": # so template
                if ref_field == 'product_id':
                    return sol_browse[0].product_id.id
                else: # family
                    return get_product_from_template(
                        self, cr, uid, sol_browse[0].family_id.id, 
                        context=context)
        except:
            return False
            
        try:
            if field == "bom":        
                if ref_field == 'product_id':
                    tmpl_id = sol_browse[0].product_id.product_tmpl_id.id
                else: # family
                    tmpl_id = sol_browse[0].family_id.id                

                # Search BOM for template:
                item_ids = self.pool.get("mrp.bom").search(
                    cr, uid, [(
                        'product_tmpl_id', '=', tmpl_id), ], context=context)
                if item_ids:
                    return item_ids[0]
                else: 
                    return False    
        except:
            return False    

        for item in sol_browse:
            if old_product_id == False:
                old_product_id = item.__getattribute__(ref_field).id
                
            # Test function mode:
            if field == "list":
                if item.__getattribute__(ref_field).id != old_product_id:
                    res = "Error! Choose order line that are of one product ID"
                    break                                    
                         
                res += """
                    <tr>
                        <td>%s [%s] </td>
                        <td>%s</td>
                        <td>%s</td>
                    </tr>""" % (
                        item.order_id.name,
                        item.sequence,
                        item.product_uom_qty,
                        "%s/%s/%s" % (
                            item.date_deadline[8:10],
                            item.date_deadline[5:7],
                            item.date_deadline[:4],
                            ) if item.date_deadline else _("Not present!")
                        )
            elif field == "error":
                if item.__getattribute__(ref_field).id != old_product_id:
                    return True
            elif field in ("oc_total", "total"):
                res += item.product_uom_qty or 0.0
            elif field in ("from_deadline", "to_deadline"):
                if not res:
                    res = item.date_deadline
                if field == "from_deadline":
                    if item.date_deadline < res:
                        res = item.date_deadline
                else: # to_deadline
                    if item.date_deadline > res:
                        res = item.date_deadline
        else:
            if field == "list":
                res += "</table>" # close table for list element
        return res
   
    _columns = {
        'name': fields.text('OC line', readonly=True),
        
        'oc_total': fields.float(
            'OC Total', digits=(16, 2), readonly=True),
        'total': fields.float(
            'Total', 
            digits=(16, 2), 
            required=True,
            help='Produce total'),

        'current_total': fields.float(
            'Production: Total', digits=(16, 2), readonly=True),
        'current_extra': fields.float(
            'Production: Extra', digits=(16, 2), readonly=True),

        'product_id': fields.many2one(
            'product.product', 'Product/Family'), # only for filter BOM
        'product_tmpl_id': fields.many2one(
            'product.template', 'Mod. Product/Family', required=True),
        'production_id': fields.many2one(
            'mrp.production', 'Production'),
        'bom_id': fields.many2one('mrp.bom', 'BOM'),
        'item_hour': fields.float(
            'Item per hour', digits=(16, 2),
            help="For generare lavoration (required when BOM not present"),
        
        'from_deadline': fields.date('From deadline', 
            help='Min deadline found in order line!',
            readonly=True),
        'to_deadline': fields.date('To deadline', 
            help='Max deadline found in order line!',
            readonly=True),

        # Error control:
        'is_error': fields.boolean('Is error'),
        'error': fields.text('Error', readonly=True),
        'warning': fields.text('Warning', readonly=True),
        'operation':fields.selection([
            ('create', 'Create'),
            ('append', 'Append'),            
            ], 'Operation', select=True, required=True),
        }
        
    _defaults = {
        'name':  lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, "list", context=c),
        #'all_in_one': lambda *a: False,
        'is_error': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, "error", context=c),
        'oc_total': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, "oc_total", context=c),        
        'total': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, "total", context=c),        
        'product_id': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, "product", context=c),        
        'product_tmpl_id': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, "template", context=c),        
        'bom_id': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, "bom", context=c),        
        'from_deadline': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, "from_deadline", context=c),        
        'to_deadline': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, "to_deadline", context=c),        
        'operation': lambda *x: 'create',    
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: