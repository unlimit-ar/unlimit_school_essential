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


class SchoolInscription(ModelSQL, ModelView):
    'School Inscription'
    __name__ = 'school.inscription'

    year = fields.Integer('Year')
    student = fields.Many2One('party.party', 'Student', domain=[('is_student', '=', True)])
    level = fields.Many2One('school.level', 'Level')
    level_year = fields.Many2One('school.level.year', 'Level Year', domain=[('level', '=', Eval('level'))])
    extra_products = fields.Many2Many('school.inscription-extra.product', 'incription', 'extra_product', 'Extra Products')
    scholarship = fields.Numeric('scholarship', digits=(3,0))

    @staticmethod
    def default_year():
        return datetime.today().year
    
    @staticmethod
    def default_scholarship():
        return Decimal(0)
    
    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
            ('student',) + tuple(clause[1:]),
            ]

    def get_rec_name(self, name):
        student = self.student
        level_year = self.level_year.name
        name = student.name
        if student.lastname:
            name = ', '.join([student.lastname, student.name])
        return '[' +level_year + '] ' + name
    
    @classmethod
    def write(cls, inscriptions, values, *args):
        super(SchoolInscription, cls).write(inscriptions, values, *args)
        Payment = Pool().get('school.payment')
        for inscription in inscriptions:
            payments = Payment.search([('inscription', '=', inscription), ('state', '=', 'must')])
            Payment.update_ammount(payments)

    
class SchoolInscriptionExtraProduct(ModelSQL):
    'School Inscription Extra Products'
    __name__ = 'school.inscription-extra.product'

    incription = fields.Many2One('school.inscription', 'Inscription' )
    extra_product = fields.Many2One('school.extra.product', 'Extra Product')


class WizardSchoolInscription(Wizard):
    'Wizard School Inscription'
    __name__ = 'wizard.school.inscription'

    start = StateView('school.inscription',
        'unlimit_school_essential.school_inscription_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('OK', 'add', 'tryton-ok', True),
            ])
    add = StateTransition()

    def default_start(self, fields):
        year = datetime.today().year
        res = {
            'year': str(year),
            }
        return res

    def transition_add(self):
        pool = Pool()
        parts = ['Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        extra = [e.name for e in self.start.extra_products]
        payments = []
        SchoolInscription = pool.get('school.inscription')
        SchoolPayments = pool.get('school.payment')
        school_inscriptions = SchoolInscription.search([('year', '=', self.start.year),
                                 ('student', '=', self.start.student)])
        if school_inscriptions:
            raise UserError(
                gettext('unlimit_school_essential'
                '.msg_school_inscription'))

        school_inscription, = SchoolInscription.create([{
            'year':self.start.year,
            'student':self.start.student,
            'level':self.start.level,
            'level_year':self.start.level_year,
            'extra_products':[('add',[e.id for e in self.start.extra_products])],
        }])

        SchoolProduct = pool.get('school.product')
        try:
            school_product, = SchoolProduct.search([('level', '=', self.start.level), ('type', '=', 'share'),('paid', '=', False)])
            inscription_product, = SchoolProduct.search([('level', '=', self.start.level), ('type', '=', 'inscription'),('paid', '=', False)])
        except:
            raise UserError('Falta configurar productos.')
        
        for month in zip(range(3,13), parts):
            payments.append({
                'name': month[1],
                'date': datetime(year=self.start.year, month=month[0], day=1).date(),
                'inscription': school_inscription,
                'product': school_product,
                'amount_paid': Decimal(0),
                # 'amount_paid': school_product.amount_with_extra_products(extra),
                'type': 'share',
            })

        for part, month in zip(range(1, inscription_product.part +1 ),range(13-inscription_product.part +1, 13)):
            payments.append({
                'date': datetime(year=self.start.year -1, month=month, day=1).date(),
                'name': str(part) + ' Cuota',
                'inscription': school_inscription,
                'product': inscription_product,
                'amount_paid': Decimal(0),
                # 'amount_paid': inscription_product.total_amount,
                'type': 'inscription',
            })
        
        SchoolPayments.update_ammount(SchoolPayments.create(payments)) 

        return 'end' # si sale todo bien
