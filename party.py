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
    family = fields.Many2One('school.family', 'Family')
    # family = fields.One2Many('school.family', 'party', 'Family')
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
    contact_mechanisms_function = fields.Function(fields.One2Many(
        'party.contact_mechanism', None, "Contact Mechanisms", states={'readonly':True}), 'get_contact_mechanisms')
    inscriptions = fields.One2Many('school.inscription', 'student', 'Inscriptions')
    
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
        
    
    def get_contact_mechanisms(self, name):
        contacts = []
        contacts.extend(self.contact_mechanisms)
        if not self.family:
            return contacts
        for family in self.family.members:
            contacts.extend(family.party.contact_mechanisms)
        return contacts
    
    # @staticmethod
    # def default_is_student():
    #     return True


class Family(ModelSQL, ModelView):
    'Family'
    __name__ = 'school.family'

    name = fields.Char('Family', required=True, help='Family code')

    members = fields.One2Many(
        'school.family_member', 'family', 'Family Members')
    
    students_members = fields.Function(fields.One2Many('party.party', None, 'Students'), 'get_students_members') 

    info = fields.Text('Extra Information')

    @classmethod
    def __setup__(cls):
        super(Family, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('name_uniq', Unique(t, t.name),
             'The Family Code must be unique !'),
        ]

    def get_students_members(self, name):
        pool = Pool()
        Party = pool.get('party.party')
        partys = Party.search([('family', '=', self.id), ('is_student', '=', True)])
        return [p.id for p in partys]


class FamilyMember(ModelSQL, ModelView):
    'Family Member'
    __name__ = 'school.family_member'

    family = fields.Many2One(
        'school.family', 'Family', required=True, readonly=True,
        help='Family code')

    party = fields.Many2One(
        'party.party', 'Party', required=True,
        domain=[('is_person', '=', True)],
        help='Family Member')

    role = fields.Char('Role', help='Father, Mother, sibbling...')
