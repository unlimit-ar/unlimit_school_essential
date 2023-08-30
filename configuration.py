import re
import pytz
from datetime import datetime
from sql import Literal

from trytond.model import DeactivableMixin, fields, Unique, ModelSQL, ModelView, ModelSingleton
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Or, Id
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class SchoolProductsConfiguration(ModelSQL):
    "School Products Configuration"
    __name__ = 'school.configuration-product.product'
    config = fields.Many2One(
        'school.configuration', "Configuration",
        required=True, ondelete='CASCADE')
    product = fields.Many2One(
        'product.product', "Product",
        required=True, ondelete='CASCADE')


class Configuration(ModelSingleton, ModelSQL, ModelView):
    'School Configuration'
    __name__ = 'school.configuration'

    products = fields.Many2Many(
        'school.configuration-product.product', 'config', 'product', "Product")
    payment_sequence = fields.Many2One('ir.sequence', "Payment Sequence",
        domain=[
            ('sequence_type', '=', Id('unlimit_school_essential', 'sequence_type_school_payment')),
            ])

