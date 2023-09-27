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

    @staticmethod
    def default_state():
        return 'must'
    

class SchoolPaymentReport(Report):
    __name__ = 'school.payment.report'
