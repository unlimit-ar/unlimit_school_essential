import re
import pytz
from datetime import datetime
from sql import Column, Literal
import calendar
from decimal import Decimal

from trytond.model import DeactivableMixin, fields, Unique, ModelSQL, ModelView, Workflow, sequence_ordered
from trytond.wizard import Wizard, Button, StateView, StateTransition
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Or, Id
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.report import Report
from trytond.i18n import gettext


class SchoolPayment(ModelSQL, ModelView):
    'School Payment'
    __name__ = 'school.payment'

    name = fields.Char('Name')
    inscription = fields.Many2One('school.inscription', 'Inscription')
    product = fields.Many2One('school.product', 'Product')
    state = fields.Selection([
        ('paid', 'Paid'),
        ('must', 'Must')], 'State', readonly=True)
    amount_paid = fields.Numeric('Amount Paid')
    student = fields.Function(fields.Many2One('party.party', 'Student'), 'get_studet',
                              searcher='search_student')
    year = fields.Function(fields.Integer('Year'), 'get_year', searcher='search_year')
    currency = fields.Many2One('currency.currency', 'Currency')

    @staticmethod
    def default_state():
        return 'must'
    
    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.id

    def get_studet(self, name):
        if self.inscription:
            return self.inscription.student.id
    
    def get_year(self, name):
        if self.inscription:
            return self.inscription.year
    
    @classmethod
    def search_student(cls, name, clause):
        return [('inscription.student',) + tuple(clause[1:])]
    
    @classmethod
    def search_year(cls, name, clause):
        return [('inscription.year',) + tuple(clause[1:])]

    

class SchoolPaymentReport(Report):
    __name__ = 'school.payment.report'


class SchoolAccountStatusContext(ModelView):
    'Payment Income'
    __name__ = 'school.account.status.context'

    level = fields.Many2One('school.level', 'Level')
    level_year = fields.Many2One('school.level.year', 'Level Year')
    student = fields.Many2One('party.party', 'Student', domain=[('is_student', '=', True)])


class SchoolAccountStatus(ModelSQL, ModelView):
    'School Account Status'
    __name__ = 'school.account.status'

    payment = fields.Many2One('school.payment', 'Payment')
    student = fields.Function(fields.Many2One('party.party', 'Student'), 'get_student')

    @classmethod
    def table_query(cls):
        pool = Pool()
        columns = []
        context = Transaction().context
        Payment = pool.get('school.payment')
        Inscription = pool.get('school.inscription')
        payment = Payment.__table__()
        inscription = Inscription.__table__()
        where = Literal(True)
        columns = []
        for fname, field in cls._fields.items():
            if hasattr(field, 'set'):
                continue
            if fname == 'payment':
                column = Column(payment, 'id').as_(fname)
            else:
                column = Column(payment, fname).as_(fname)
            columns.append(column)
        if context.get('level'):
            where &= (inscription.level == context.get('level'))
        if context.get('level_year'):
            where &= (inscription.level_year == context.get('level_year'))
        if context.get('student'):
            where &= (inscription.student == context.get('student'))
        return payment.join(inscription, condition=inscription.id == payment.inscription).select(*columns, where=where)
        
    def get_student(self, name):
        return self.payment.student