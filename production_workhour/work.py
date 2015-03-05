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

class HrWorkhour(orm.Model):
    ''' Class for manage Work hour
    '''

    _name = 'hr.workhour'
    _description = 'Employee work hour'
            
    _columns = {
        'name': fields.char('Work hour', size=64, required=True),
        'note': fields.text('Note'),
        }

class HrWorkhourDay(orm.Model):
    ''' Class for manage Work hour for each day of the week
    '''
    
    _name = 'hr.workhour.day'
    _description = 'Employee work hour'
    _rec_name = 'weekday'

    # weekday python value:
    get_weekday = [ 
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
        ]
            
    _columns = {
        'workhour_id': fields.many2one('hr.workhour', 'Workhour'),
        'weekday': fields.selection(
            get_weekday, 'Weekday', select=True, readonly=False),
        'hour': fields.integer('Label')            
        }
        
    _defaults = {
        'hour': lambda *x: 8,
        }    

class HrWorkhour(orm.Model):
    ''' Class for manage Work hour
    '''

    _inherit = 'hr.workhour'
    
    _columns = {
        'day_ids': fields.one2many('hr.workhour.day', 'workhour_id', 'Day'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: