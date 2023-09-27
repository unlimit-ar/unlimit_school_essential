import re
import pytz
from datetime import datetime
from sql import Literal
from dateutil.relativedelta import relativedelta

from trytond.model import DeactivableMixin, fields, Unique, ModelSQL, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Or, Not, And
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
# from trytond.modules.party_ar.party import TIPO_DOCUMENTO

TIPO_DOCUMENTO = [
    ('80', 'CUIT'),
    ('86', 'CUIL'),
    ('96', 'DNI'),
    ]

_STATES={'invisible': Bool(Eval('is_student'))}
_STATES_STUDENT={'required': Bool(Eval('is_student'))}
_STATES_FAMILY={'required': And(Bool(Eval('is_person')), Not(Bool(Eval('is_student'))))}


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    lastname = fields.Char('Last Name', states={'required': Bool(Eval('is_person'))})
    doc_number = fields.Char('Doc Number', states={'required': Bool(Eval('is_person'))})
    is_person = fields.Boolean('Person',
        help='Check if the party is a person.')
    is_student = fields.Boolean('Student',
        help='Check if the party is a student.')
    family = fields.One2Many('party.family', 'party', 'Family', help='Family Members')
    # family = fields.One2Many('party.party', 'parent', 'Family', domain=[('is_person', '=', True)], help='Family Members')
    gender = fields.Selection((
        (None, ''),
        ('men', 'Men'),
        ('women', 'Women'),
        ('x', 'X'),
        ), 'Gender', 
        states=_STATES_STUDENT, 
        sort=False)
    dob = fields.Date('Date of Birth', help='Date of Birth', states=_STATES_STUDENT)
    age = fields.Function(fields.Char('Age'), 'person_age')
    citizenship = fields.Many2One(
        'country.country', 'Citizenship', help='Country of Citizenship', 
        states={'required': Bool(Eval('is_person'))})
    employment = fields.Char('Employment', states=_STATES_FAMILY)
    studies = fields.Char('Studies', states=_STATES_FAMILY)
    # inscriptions = fields.One2Many('school.inscription', 'student', 'Inscriptions', states={'readonly':True})
    
    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.tipo_documento.selection = TIPO_DOCUMENTO
        cls.name.states.update(_STATES_STUDENT)
        t = cls.__table__()
        cls._sql_constraints = [
            ('doc_number_uniq', Unique(t, t.doc_number),
                'unlimit_school_essential.msg_doc_number_unique'),
        ]


    @classmethod
    def view_attributes(cls):
        return [
            ('//group[@id="student"]', 'states', {
                    'invisible': ~Eval('is_student'),
                    }),
            ('//group[@id="family"]', 'states', {
                    'invisible': Eval('is_student'),
                    }),
            ]

    @staticmethod
    def default_is_person():
        return True

    @staticmethod
    def default_tipo_documento():
        return '96'

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
            ('doc_number',) + tuple(clause[1:]),
            ('lastname',) + tuple(clause[1:]),
            ]

    def get_rec_name(self, name):
        name = self.name
        if self.lastname:
            name = ', '.join([self.lastname, self.name])
        return name

    def person_age(self, name):
        today = datetime.today().date()

        if self.dob:
            start = datetime.strptime(str(self.dob), '%Y-%m-%d')
            end = datetime.strptime(str(today), '%Y-%m-%d')

            rdelta = relativedelta(end, start)

            years_months_days = str(rdelta.years) + 'y ' \
                + str(rdelta.months) + 'm ' \
                + str(rdelta.days) + 'd'
            
            return years_months_days


class Family(ModelSQL, ModelView):
    'Family'
    __name__ = 'party.family'

    party = fields.Many2One('party.party', 'Party')
    parent = fields.Many2One('party.party', 'Parent', domain=[('is_person', '=', True)])
    rol = fields.Char('Rol')