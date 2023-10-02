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


