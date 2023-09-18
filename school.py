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


class SchoolYear(Workflow, ModelSQL, ModelView):
    'School Year'
    __name__ = 'school.year'

    name = fields.Char('Year', required=True)
    products = fields.One2Many('school.product', 'year', 'Products')
    enrollment = fields.Many2One('school.product', 'Enrollment', domain=[('year', '=', None), ('state', '=', None)])
    state = fields.Selection([
            ('draft', 'Draft'),
            ('in_caming', 'In Caming'),
            ('in_progress', 'In Progress'),
            ('end', 'End'),
        ], 'State', readonly=True)
    
    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._transitions |= {
            ('draft', 'in_caming'),
            ('in_caming', 'in_progress'),
            ('in_progress', 'end'),
            }
        cls._buttons.update({
            'autocomplete_products': {
                    'invisible': Eval('state') != 'draft',
                    'depends': ['state'],
                    },
            'in_caming': {
                    'invisible': Eval('state') != 'draft',
                    'depends': ['state'],
                    },
            'in_progress': {
                    'invisible': Eval('state') != 'in_caming',
                    'depends': ['state'],
                    },
            'end': {
                    'invisible': Eval('state') != 'in_progress',
                    'depends': ['state'],
                    },
            })

    @staticmethod
    def default_state():
        return 'draft'
    
    @classmethod
    @ModelView.button
    @Workflow.transition('in_caming')
    def in_caming(cls, school_years):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('in_progress')
    def in_progress(cls, school_years):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('end')
    def end(cls, school_years):
        pass

    @classmethod
    @ModelView.button
    def autocomplete_products(cls, school_years):
        pool = Pool()
        to_create = []
        Configuration = pool.get('school.configuration')
        SchoolProduct = pool.get('school.product')
        config_products = Configuration(1).products
        for year in school_years:
            sps = [sp.product.id for sp in year.products]
            for p in config_products:
                if not p.id in sps:
                    to_create.append({'product':p.id, 'amount': p.list_price, 'year':year.id})
        if to_create:
            SchoolProduct.create(to_create)

    # @classmethod
    # def write(cls, years, values, *args):
    #     pool = Pool()
    #     SchoolProduct = pool.get('school.product')
    #     super(SchoolYear, cls).write(years, values, *args)
    #     if 'products' in values.keys():
    #         SchoolProduct.update_amount(years)


class SchoolProduct(sequence_ordered(), ModelSQL, ModelView):
    'School Product'
    __name__ = 'school.product'

    year = fields.Many2One('school.year', 'Year')
    inscription = fields.Many2One('school.inscription', 'Inscription')
    payment = fields.Many2One('school.payment', 'Payment')
    product = fields.Many2One('product.product', 'Products')
    amount = fields.Numeric('Amount', digits=(16,2))
    part = fields.Integer('Part')
    currency = fields.Many2One('currency.currency', 'Currency')
    state = fields.Selection([
        (None, ''),
        ('paid', 'Paid'),
        ('must', 'Must')
        ], 'State')

    def get_rec_name(self, name):
        if self.part:
            return str(self.part) + ' ' + self.product.rec_name
        return self.product.rec_name
    
    @classmethod
    def update_amount(cls, years):
        for year in years:
            school_products = cls.seach([('inscription.year', '=', year), ('state', '!=', 'paid')])
        import pdb;pdb.set_trace()
        pass

    @classmethod
    def write(cls, products, values, *args):
        args2 = list(args)
        sps = []
        actions = iter((products, values) + args)
        if products:
            for records, values2 in zip(actions, actions):
                year = getattr(products[0], 'year', None)
                sps = cls.search([('inscription.year', '=', year), ('state', '=', 'must'), ('product', 'in', [p.product for p in records])])
                args2.append(sps)
                args2.append(values2)
        super(SchoolProduct, cls).write(products, values, *args2)

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.id
        
    @staticmethod
    def default_part():
        return 1


class SchoolLevel(ModelSQL, ModelView):
    'School Level'
    __name__ = 'school.level'

    name = fields.Char('Name')


class SchoolSection(ModelSQL, ModelView):
    'School Section'
    __name__ = 'school.section'
    
    name = fields.Char('Name')
  

class SchoolGrade(ModelSQL, ModelView):
    'School Grade'
    __name__ = 'school.grade'

    name = fields.Char('Name')


class SchoolFeeType(ModelSQL, ModelView):
    'Fee Type'
    __name__ = 'school.fee.type'

    name = fields.Char('Name')


class SchoolConfigStart(ModelView):
    'School Config'
    __name__ = 'school.config.start'


class SchoolConfig(Wizard):
    'School Company'
    __name__ = 'school.config'
    start = StateView('school.config.start',
        'unlimit_school_essential.school_config_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('OK', 'add', 'tryton-ok', True),
            ])
    add = StateTransition()

    def transition_add(self):
        pool = Pool()
        Product = pool.get('product.product')
        ProductTemplate = pool.get('product.template')
        Uom = pool.get('product.uom')
        products_template = []
        for index, month in enumerate([calendar.month_name[i] for i in range(1,13)]):
            products_template.append({
                'name': month,
                'code': str(index+1),
                'list_price': Decimal('0'),
                'type': 'service',
                'default_uom': Uom.search([('name', '=', 'Unit')], limit=1)[0].id,
                'products':[('create', [{}])]
            }) 
        ProductTemplate.create(products_template)
        return 'end'

    def end(self):
        return 'reload context'
    

class SchoolInscription(ModelSQL, ModelView):
    'School Inscription'
    __name__ = 'school.inscription'

    year = fields.Many2One('school.year', 'School Year', domain=[('state', 'in', ['in_caming', 'in_progress'])], required=True)
    student = fields.Many2One('party.party', 'Student', domain=[('is_student', '=', True)], required=True)
    doc_number = fields.Function(fields.Char('Document Number', readonly=True), 'on_change_with_doc_number')
    level = fields.Many2One('school.level', 'Level')
    section = fields.Many2One('school.section', 'Section')
    grade = fields.Many2One('school.grade', 'Grade', required=True)
    fee_type = fields.Many2One('school.fee.type', 'Fee Type')
    enrollment_fraction = fields.Integer('Enrollment Fraction', required=True)
    products = fields.One2Many('school.product', 'inscription', 'Products')

    @staticmethod
    def default_enrollment_fraction():
        return 3

    @fields.depends('student', '_parent_student.doc_number')
    def on_change_with_doc_number(self, name=None):
        res = None
        if self.student:
            res = self.student.doc_number
        return res


class SchoolInscriptionStudent(Wizard):
    'School Incription Student'
    __name__ = 'school.inscription.student'

    start = StateView('school.inscription',
        'unlimit_school_essential.school_inscription_wizard_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('OK', 'add', 'tryton-ok', True),
            ])
    add = StateTransition()

    def transition_add(self):
        pool = Pool()
        SchoolInscription = pool.get('school.inscription')
        SchoolProduct = pool.get('school.product')
        domain = [('year', '=', self.start.year),
                  ('student', '=', self.start.student)
                  ]
        school_inscriptions = SchoolInscription.search(domain)
        if not school_inscriptions:
            school_products = []
            #Crear la inscriptcion
            
            amount_fractionDraft = Decimal(self.start.year.enrollment.amount/self.start.enrollment_fraction).quantize(Decimal('0.00'))
            for fraction in range(1,self.start.enrollment_fraction+1):
                enrollment, = SchoolProduct().copy([self.start.year.enrollment])
                enrollment.amount = amount_fraction
                enrollment.state = 'must'
                enrollment.part = fraction
                enrollment.save()
                school_products.append(enrollment)
            
            copys = SchoolProduct().copy(self.start.year.products, default={'year':None, 'state': 'must'})
            school_products.extend(copys)
            
            to_create = {
                'year': self.start.year,
                'student': self.start.student,
                'level': self.start.level,
                'section': self.start.section,
                'grade': self.start.grade,
                'fee_type': self.start.fee_type,
                'products': [('add', [sp.id for sp in school_products])],
            }
            SchoolInscription.create([to_create])
            pass
        else:
            #Devolver error y avisar q ese escolar ya esta inscripto
            raise UserError(
                gettext('unlimit_school_essential'
                '.msg_school_inscription'))
        return 'end'
