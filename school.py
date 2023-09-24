import re
import pytz
from datetime import datetime
from sql import Literal
import calendar
from decimal import Decimal

from trytond.model import DeactivableMixin, fields, Unique, ModelSQL, ModelView, Workflow, sequence_ordered
from trytond.wizard import Wizard, Button, StateView, StateTransition
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Or, Id
from trytond.transaction import Transaction
from trytond.exceptions import UserError

from trytond.i18n import gettext


class SchoolProduct(ModelSQL, ModelView):
    'School Product'
    __name__ = 'school.product'

    type = fields.Selection([
            ('inscription', 'Inscription'),
            ('share', 'Share')
        ], 'Type')
    type_string = type.translated('type')
    level = fields.Many2One('school.level', 'Level')
    lines = fields.One2Many('school.product.line', 'product', 'Line')
    total_amount = fields.Function(fields.Numeric('Total Amount'), 'on_change_with_total_amount')
    # amount = fields.Numeric('Amount', digits=(16,2))
    part = fields.Integer('Part', states={'invisible': Bool(Eval('share'))})
    currency = fields.Many2One('currency.currency', 'Currency')
    state = fields.Selection([
        (None, ''),
        ('paid', 'Paid'),
        ('must', 'Must')
        ], 'State')

    @classmethod
    def __setup__(cls):
        super(SchoolProduct, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints += [
            ('level_uniq', Unique(table, table.level),
                'unlimit_school_essential.msg_level_uniq')
        ]

    def get_rec_name(self, name):
        if self.part:
            return str(self.part) + ' ' + self.product.rec_name
        return self.product.rec_name
    
    @fields.depends('lines')
    def on_change_with_total_amount(self, name=None):
        total_amount = Decimal('0')
        for line in self.lines:
            total_amount += line.amount
        return total_amount
    
    @classmethod
    def update_amount(cls, years):
        for year in years:
            school_products = cls.seach([('inscription.year', '=', year), ('state', '!=', 'paid')])
        import pdb;pdb.set_trace()
        pass

    # @classmethod
    # def write(cls, products, values, *args):
    #     args2 = list(args)
    #     sps = []
    #     actions = iter((products, values) + args)
    #     if products:
    #         for records, values2 in zip(actions, actions):
    #             year = getattr(products[0], 'year', None)
    #             sps = cls.search([('inscription.year', '=', year), ('state', '=', 'must'), ('product', 'in', [p.product for p in records])])
    #             args2.append(sps)
    #             args2.append(values2)
    #     super(SchoolProduct, cls).write(products, values, *args2)

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.id
        
    @staticmethod
    def default_part():
        return 1
    
    @staticmethod
    def default_share():
        return 'share'


class SchoolProductLine(ModelSQL, ModelView):
    'School Product Line'
    __name__ = 'school.product.line'

    product = fields.Many2One('school.product', 'Product')
    name = fields.Char('Name', required=True)
    amount = fields.Numeric('Amount', digits=(16,2), required=True)

    def default_amount():
        return '0'


class SchoolLevel(ModelSQL, ModelView):
    'School Level'
    __name__ = 'school.level'

    name = fields.Char('Name')
    year = fields.One2Many('school.level.year', 'level', 'Year')


class SchoolLevelYear(ModelSQL, ModelView):
    'School Level Year'
    __name__ = 'school.level.year'

    name = fields.Char('Name', states={'required': True})
    level = fields.Many2One('school.level', 'Level')
    shift_time = fields.Selection([
            (None, ''),
            ('TT', 'TT'),
            ('TM', 'TM')
        ], 'Shift Time')
    
    def get_rec_name(self, name):
        if self.shift_time:
            return '[' + self.shift_time + '] ' + self.name
        return self.name