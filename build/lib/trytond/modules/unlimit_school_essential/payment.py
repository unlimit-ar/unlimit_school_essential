import re
import pytz
from datetime import datetime
from sql import Literal
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from trytond.model import DeactivableMixin, fields, Unique, ModelSQL, ModelView, Workflow
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Or, Not
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.report import Report
# from trytond.modules.party_ar.party import TIPO_DOCUMENTO

PRODUCTS_DOMAIN = [
    ('inscription.year', '=', Eval('year')),
    ('inscription.student', '=', Eval('student')),
]

class SchoolPayment(Workflow, ModelSQL, ModelView):
    "Payment"
    __name__ = "school.payment"

    name = fields.Char('Number', readonly=True)
    date = fields.Date('Date', required=True)
    year = fields.Many2One('school.year', 'School Year', domain=[('state', 'in', ['in_caming','in_progress'])], required=True)
    student = fields.Many2One('party.party', 'Student', domain=[('is_student', '=', True)], required=True)
    doc_number = fields.Function(fields.Char('Document Number', readonly=True), 'on_change_with_doc_number')
    products = fields.One2Many('school.product', 'payment', 'Products', domain=PRODUCTS_DOMAIN,
        add_remove=[
            ('inscription.year', '=', Eval('year')),
            ('inscription.student', '=', Eval('student')),
            ('state', '=', 'must')
        ], states={'readonly': Eval('state') == 'payed'}, depends=['state', 'student', 'year'])
    total_pay = fields.Function(fields.Numeric('Total to Pay', digits=(16,2)), 'on_change_with_total_pay')
    products_list = fields.Function(fields.Char('List Products'), 'get_products_list', searcher='search_product')
    currency = fields.Many2One('currency.currency', 'Currency', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('payed', 'Payed'),
        ('canceled', 'Canceled')
        ], 'State', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('date', 'ASC'))
        cls._transitions |= {
            ('draft', 'payed'),
            ('draft', 'canceled'),
            }
        cls._buttons.update({
            'pay': {
                    'invisible': Eval('state') != 'draft',
                    'depends': ['state'],
                    },
            'cancel': {
                    'invisible': Eval('state') != 'draft',
                    'depends': ['state'],
                    },
            })

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        company = Transaction().context.get('company')
        if company:
            company = Company(company)
            return company.currency.id

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_date():
        return datetime.today().date()

    @fields.depends('products')
    def on_change_with_total_pay(self, name=None):
        res = 0
        for product in self.products:
            if product.amount:
                res += product.amount
        return Decimal(res)

    @fields.depends('student', '_parent_student.doc_number')
    def on_change_with_doc_number(self, name=None):
        res = None
        if self.student:
            res = self.student.doc_number
        return res

    @classmethod
    def _new_code(cls, **pattern):
        pool = Pool()
        Configuration = pool.get('school.configuration')
        config = Configuration(1)
        sequence = config.payment_sequence
        if sequence:
            return sequence.get()

    @classmethod
    @ModelView.button
    @Workflow.transition('payed')
    def pay(cls, pays):
        for pay in pays:
            pay.name = cls._new_code()
            for product in pay.products:
                product.state = 'paid'
                product.save()
        cls.save(pays)

    @classmethod
    @ModelView.button
    @Workflow.transition('canceled')
    def cancel(cls, pays):
        pass

    def get_products_list(self, name):
        res = ''
        if self.products:
            res = ', '.join([p.rec_name for p in self.products])
        return res
    
    @classmethod
    def search_product(cls, name, clause):
        return [('products.product',) + tuple(clause[1:])]

class SchoolPaymentReport(Report):
    __name__ = 'school.payment.report'


class SchoolPaymentIncome(ModelView):
    'Payment Income'
    __name__ = 'school.payment.income.context'

    year = fields.Many2One('school.year', 'Year')
    level = fields.Many2One('school.level', 'Level')
    section = fields.Many2One('school.section', 'Section')
    grade = fields.Many2One('school.grade', 'Grade')


class SchoolPaymentIncome(ModelSQL, ModelView):
    'Payment Income'
    __name__ = 'school.payment.income'

    

# class SchoolPaymentIncome(ModelView):
#     'Payment Income'
#     __name__ = 'school.payment.income'

#     start_date = fields.Date('Start Date', required=True)
#     end_date = fields.Date('End Date')
#     year = fields.Many2One('school.year', 'Year')
#     level = fields.Many2One('school.level', 'Level')
#     section = fields.Many2One('school.section', 'Section')
#     grade = fields.Many2One('school.grade', 'Grade')
#     student = fields.Many2One('party.party', 'Student', domain=[('is_student', '=', True)])
#     payments = fields.One2Many('school.payment', None, 'Grade', readonly=True)
#     total_amount = fields.Numeric('Total Amount', readonly=True)

#     # @classmethod
#     # def __setup__(cls):
#     #     super().__setup__()
#     #     cls._buttons.update({
#     #         'update': {},
#     #         })
    
#     @classmethod
#     def update(cls):
#         payments_income = []
#         import pdb;pdb.set_trace()
#         pool = Pool()
#         Payment = pool.get('school.payment')
#         for payment_income in payments_income:
#             start_date = payment_income.start_date
#             end_date = payment_income.end_date if payment_income.end_date else payment_income.start_date
#             if not start_date <= end_date:
#                 # TODO return error
#                 pass
#             domain = [('date', '<=', end_date),('date', '>=', start_date)]
#             if payment_income.year:
#                 domain.append(('year', '=', payment_income.year.id))
#             if payment_income.level:
#                 domain.append(('student.level', '=', payment_income.level.id))
#             if payment_income.section:
#                 domain.append(('student.section', '=', payment_income.section.id))
#             if payment_income.grade:
#                 domain.append(('student.grade', '=', payment_income.grade.id))
#             if payment_income.student:
#                 domain.append(('student', '=', payment_income.student.id))
#             payments = Payment.search(domain)
#             payment_income.payments = payments
#             payment_income.total_amount = payment_income.get_total_amount()
#         pass

#     def get_total_amount(self):
#         res = 0
#         for payment in self.payments:
#             res += payment.total_pay