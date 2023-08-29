import re
import pytz
from datetime import datetime
from sql import Literal
from dateutil.relativedelta import relativedelta

from trytond.model import DeactivableMixin, fields, Unique, ModelSQL, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Or, Not
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
# from trytond.modules.party_ar.party import TIPO_DOCUMENTO


class Product(metaclass=PoolMeta):
    "Product Variant"
    __name__ = "product.product"
    _order_name = 'rec_name'


    