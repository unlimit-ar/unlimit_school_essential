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

    @staticmethod
    def default_year():
        return datetime.today().year


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
        }])

        SchoolProduct = pool.get('school.product')
        try:
            school_product, = SchoolProduct.search([('level', '=', self.start.level), ('type', '=', 'share')])
            inscription_product, = SchoolProduct.search([('level', '=', self.start.level), ('type', '=', 'inscription')])
        except:
            raise UserError('Falta configurar productos.')
        
        for month in parts:
            payments.append({
                'name': month,
                'inscription': school_inscription,
                'product': school_product,
                'amount_paid': school_product.total_amount,
                'type': 'share',
            })
        
        for part in range(1, inscription_product.part +1 ):
            payments.append({
                'name': str(part) + ' Cuota',
                'inscription': school_inscription,
                'product': inscription_product,
                'amount_paid': inscription_product.total_amount,
                'type': 'inscription',
            })
        
        SchoolPayments.create(payments)

        return 'end' # si sale todo bien
