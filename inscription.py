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


class SchoolInscription(ModelSQL, ModelView):
    'School Inscription'
    __name__ = 'school.inscription'

    name = fields.Char('Name')
    year = fields.Integer('Year')
    student = fields.Many2One('party.party', 'Student', domain=['is_student', '=', True])
    level = fields.Many2One('school.level', 'Level')
    level_year = fields.Many2One('school.level.year', 'Level Year', domain=[('level', '=', Eval('level'))])


class SchoolPayments(ModelSQL, ModelView):
    'School Payments'
    __name__ = 'school.payments'

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