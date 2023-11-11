import re
import pytz
from datetime import datetime
from sql import Column, Literal
import calendar
from decimal import Decimal
from email.header import Header
import mimetypes

from email.mime.application import MIMEApplication
from email.mime.nonmultipart import MIMENonMultipart
from email.encoders import encode_base64
from trytond.config import config
from trytond.model import (DeactivableMixin, fields, Unique, ModelSQL, ModelView, Workflow, 
                           sequence_ordered, ModelSingleton, dualmethod)
from trytond.wizard import Wizard, Button, StateView, StateTransition, StateAction
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Or, Id, If, Equal
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.report import Report, get_email
from trytond.i18n import gettext
from trytond.sendmail import sendmail_transactional
from trytond.tools.email_ import set_from_header
from trytond.rpc import RPC


# TODO Crear un contador de emails, limitando el envio cada 24 hs a un configurable. Google permite solo 500 mails cada 24hs

def _send_email(from_, to, email_func, receipt, reports):

    from_cfg = config.get('email', 'from')
    msg, title = email_func(receipt)

    files = [
        (a[3]+'.'+a[0], a[1]) for a in reports]
    for name, data in files:
        mimetype, _ = mimetypes.guess_type(name)
        if mimetype:
            attachment = MIMENonMultipart(*mimetype.split('/'))
            attachment.set_payload(data)
            encode_base64(attachment)
        else:
            attachment = MIMEApplication(data)
        attachment.add_header(
            'Content-Disposition', 'attachment',
            filename=('utf-8', '', name))
        msg.attach(attachment)

    set_from_header(msg, from_cfg, from_ or from_cfg)
    msg['To'] = ', '.join(to)
    msg['Subject'] = Header(title, 'utf-8')
    sendmail_transactional(from_cfg, to, msg)


class SchoolPayment(ModelSQL, ModelView):
    'School Payment'
    __name__ = 'school.payment'

    name = fields.Char('Name')
    date = fields.Date('Date')
    inscription = fields.Many2One('school.inscription', 'Inscription')
    product = fields.Many2One('school.product', 'Product')
    state = fields.Selection([
        ('paid', 'Paid'),
        ('must', 'Must')], 'State', readonly=True)
    amount_paid = fields.Numeric('Amount Paid')
    student = fields.Function(fields.Many2One('party.party', 'Student'), 'get_studet',
                              searcher='search_student')
    year = fields.Function(fields.Integer('Year'), 'get_year', searcher='search_year')
    currency = fields.Many2One('currency.currency', 'Currency')
    payment_receipt = fields.Many2One('school.payment.receipt', 'Payment Receipt')
    type = fields.Selection([
            ('inscription', 'Inscription'),
            ('share', 'Share')
        ], 'Type')

    @staticmethod
    def default_state():
        return 'must'
    
    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.id

    def get_studet(self, name):
        if self.inscription:
            return self.inscription.student.id
    
    def get_year(self, name):
        if self.inscription:
            return self.inscription.year
    
    @classmethod
    def search_student(cls, name, clause):
        return [('inscription.student',) + tuple(clause[1:])]
    
    @classmethod
    def search_year(cls, name, clause):
        return [('inscription.year',) + tuple(clause[1:])]


class SchoolPaymentReport(Report):
    __name__ = 'school.payment.report'

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Language = pool.get('ir.lang')
        languages, = Language.search([
            ('code', '=', Transaction().language),
            ])

        pool = Pool()
        context = Transaction().context
        report_context = super().get_context(records, header, data)
        report_context['lang'] = languages
        return report_context
    

class SchoolAccountStatusContext(ModelView):
    'Payment Income'
    __name__ = 'school.account.status.context'

    level = fields.Many2One('school.level', 'Level')
    level_year = fields.Many2One('school.level.year', 'Level Year')
    student = fields.Many2One('party.party', 'Student', domain=[('is_student', '=', True)])
    year = fields.Integer('Year')
    date = fields.Date('Date', required=True)
    type = fields.Selection([
            ('inscription', 'Inscription'),
            ('share', 'Share')
        ], 'Type')

    @staticmethod
    def default_year():
        return datetime.today().year
    
    @staticmethod
    def default_date():
        return datetime.today().date()
    
    @staticmethod
    def default_type():
        return 'share'


class SchoolAccountStatus(ModelSQL, ModelView):
    'School Account Status'
    __name__ = 'school.account.status'

    type = fields.Function(fields.Char('Type'), 'get_type')
    inscription = fields.Many2One('school.inscription', 'Inscription')
    student = fields.Function(fields.Many2One('party.party', 'Student'), 'get_student')
    marzo = fields.Function(fields.Integer('Marzo'), 'get_share')
    abril = fields.Function(fields.Integer('Abril'), 'get_share')
    mayo = fields.Function(fields.Integer('Mayo'), 'get_share')
    junio = fields.Function(fields.Integer('Junio'), 'get_share')
    julio = fields.Function(fields.Integer('Julio'), 'get_share')
    agosto = fields.Function(fields.Integer('Agosto'), 'get_share')
    septiembre = fields.Function(fields.Integer('Septiembre'), 'get_share')
    octubre = fields.Function(fields.Integer('Octubre'), 'get_share')
    noviembre = fields.Function(fields.Integer('Noviembre'), 'get_share')
    diciembre = fields.Function(fields.Integer('Diciembre'), 'get_share')
    inscription_1 = fields.Function(fields.Integer('1 Cuota'), 'get_inscription')
    inscription_2 = fields.Function(fields.Integer('2 Cuota'), 'get_inscription')
    inscription_3 = fields.Function(fields.Integer('3 Cuota'), 'get_inscription')
    inscription_4 = fields.Function(fields.Integer('4 Cuota'), 'get_inscription')
    inscription_5 = fields.Function(fields.Integer('5 Cuota'), 'get_inscription')
    total = fields.Function(fields.Numeric('Total'), 'get_total')

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('/tree/field[@name="marzo"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="abril"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="mayo"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="junio"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="julio"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="agosto"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="septiembre"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="octubre"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="noviembre"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="diciembre"]', 'tree_invisible',
                Eval('type') == 'inscription'),
            ('/tree/field[@name="inscription_1"]', 'tree_invisible',
                Eval('type') != 'inscription'),
            ('/tree/field[@name="inscription_2"]', 'tree_invisible',
                Eval('type') != 'inscription'),
            ('/tree/field[@name="inscription_3"]', 'tree_invisible',
                Eval('type') != 'inscription'),
            ('/tree/field[@name="inscription_4"]', 'tree_invisible',
                Eval('type') != 'inscription'),
            ('/tree/field[@name="inscription_5"]', 'tree_invisible',
                Eval('type') != 'inscription'),
            ]

    @classmethod
    def table_query(cls):
        pool = Pool()
        columns = []
        context = Transaction().context
        Payment = pool.get('school.payment')
        Inscription = pool.get('school.inscription')
        payment = Payment.__table__()
        inscription = Inscription.__table__()
        where = Literal(True)
        columns = []
        for fname, field in cls._fields.items():
            if hasattr(field, 'set'):
                continue
            if fname == 'inscription':
                column = Column(inscription, 'id').as_(fname)
            else:
                column = Column(inscription, fname).as_(fname)
            columns.append(column)
        if context.get('date'):
            year = context.get('date').year
            where &= (inscription.year == year)
        if context.get('level'):
            where &= (inscription.level == context.get('level'))
        if context.get('level_year'):
            where &= (inscription.level_year == context.get('level_year'))
        if context.get('student'):
            where &= (inscription.student == context.get('student'))    
        return inscription.select(*columns, where=where)
        # return payment.join(inscription, condition=inscription.id == payment.inscription).select(*columns, where=where)
        
    def get_total(self, name):  
        pool = Pool()
        Payment = pool.get('school.payment')
        sum = 0
        payments = Payment.search([('inscription', '=', self.inscription), 
            ('state', '=', 'paid'), ('type', '=', self.type)])
        for payment in payments:
            sum += payment.amount_paid
        return sum
    
    def get_student(self, name):
        return self.inscription.student
    
    def get_type(self, name):
        context = Transaction().context
        type = context.get('type')
        return type
    
    def get_share(self, name):
        pool = Pool()
        Payment = pool.get('school.payment')

        payments = Payment.search([('inscription', '=', self.inscription), 
            ('state', '=', 'paid'), ('name', '=', name.capitalize())])
                
        if payments:
            return payments[0].amount_paid
        return 0
    
    def get_inscription(self, name):
        pool = Pool()
        Payment = pool.get('school.payment')
        payment_name = name.split('_')[1] + ' Cuota'
        payments = Payment.search([('inscription', '=', self.inscription), 
            ('state', '=', 'paid'), ('name', '=', payment_name)])
                
        if payments:
            return payments[0].amount_paid
        return 0
        

class SchoolPaymentWizardStart(ModelView):
    'School Payment Wizard Start'
    __name__ = 'school.payment.wizard.start'

    year = fields.Integer('Year', required=True)
    student = fields.Many2One('party.party', 'Student', domain=[('is_student', '=', True)], 
                              required=True,
                              depends=['year'])
    receipt = fields.Many2One('school.payment.receipt', 'Receipt')
    payments = fields.Many2Many('school.payment', None, None, "Payments", filter=[
        If(Eval('type') == 'inscription', [
            ('student', '=', Eval('student')),
            ('state', '=', 'must'),
            ('product.type', '=', 'inscription')
            ],[
            ('inscription.year', '=', Eval('year')),
            ('student', '=', Eval('student')),
            ('state', '=', 'must'),
            ('product.type', '=', 'share')])
        ], required=True)
    type = fields.Selection([
            ('inscription', 'Inscription'),
            ('share', 'Share')
        ], 'Type')
    voucher_id = fields.Char('Voucher ID')
    text = fields.Text('voucher_error', readonly=True)

class SchoolPaymentWizard(Wizard):
    'School Payment Wizard'
    __name__ = 'school.payment.wizard'

    start = StateView('school.payment.wizard.start',
        'unlimit_school_essential.school_payment_wizard_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Pay', 'pay', 'tryton-ok', default=True),
            ])
    voucher_error = StateView('school.payment.wizard.start',
        'unlimit_school_essential.school_payment_wizard_voucher_error_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Back', 'pay_ok', 'tryton-back', default=True),
            ])
    pay_ok = StateView('school.payment.wizard.start',
        'unlimit_school_essential.school_payment_wizard_pay_ok_view_form', [
            Button('Close', 'end', 'tryton-close', default=True),
            Button('Print', 'print_', 'tryton-print'),
            Button('Email', 'email', 'tryton-email'),
            ])
    
    pay = StateTransition()
    print_ = StateAction('unlimit_school_essential.report_school_payment')
    email = StateTransition()

    def transition_print_(self):
        return 'end'

    def do_print_(self, action):
        return action, {
            'id': self.start.receipt.id,
            'ids': [self.start.receipt.id],
            }
            
    def transition_email(self):
        pool = Pool()
        config = pool.get('school.configuration')(1)
        ContactMechanism = pool.get('party.contact_mechanism')
        contact_mechanisms = ContactMechanism.search([('party', '=', self.start.receipt.student), ('type', '=', 'email')])
        to = [contact_mechanism.value for contact_mechanism in contact_mechanisms]

        if config.validation_emails(len(to)):

            SchoolPaymentReceipt = pool.get('school.payment.receipt')
            SchoolPaymentReceipt.__queue__.send_receip_notify(self.start.receipt)
            return 'pay_ok'

        text = gettext('unlimit_school_essential.msg_email_cant_error')
        self.start.text = text
        return 'voucher_error'

    # def do_email_(self, action):
    #     return action, {
    #         'id': self.start.receipt.id,
    #         'ids': [self.start.receipt.id],
    #         }

    def transition_pay(self):
        pool = Pool()
        Receipt = pool.get('school.payment.receipt')
        Product = pool.get('school.product')
        if self.start.voucher_id:
            vouchers = Receipt.search([('voucher_id', '=', self.start.voucher_id)])
            if vouchers:
                voucher = vouchers[0]
                text = gettext('unlimit_school_essential.msg_voucher_id_error', code=voucher.code)
                self.start.text = text
                return 'voucher_error'
            
        receipt = Receipt(
            year=self.start.year,
            student=self.start.student,
            voucher_id=self.start.voucher_id
        )
        receipt.save()
        self.start.receipt = receipt

        for payment in self.start.payments:
            payment.payment_receipt = receipt
            payment.state = 'paid'
            payment.product, = Product.copy([payment.product], default={'paid': True})
            payment.save()
        return 'pay_ok'
    
    def default_start(self, fields):
        return {'year': datetime.today().year}

    def default_voucher_error(self, fields):
        return {'text': self.start.text}


class SchoolPaymentReceiptReport(Report):
    __name__ = 'school.payment.receipt'

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Language = pool.get('ir.lang')
        languages, = Language.search([
            ('code', '=', Transaction().language),
            ])

        pool = Pool()
        context = Transaction().context
        report_context = super().get_context(records, header, data)
        report_context['lang'] = languages
        return report_context


class SchoolPaymentReceipt(ModelSQL, ModelView): 
    'School Payment Receipt'
    __name__ = 'school.payment.receipt'
    _rec_name='code'

    date = fields.DateTime('Date Time')
    code = fields.Char('Code', readonly=True)
    year = fields.Integer('Year', required=True)
    student = fields.Many2One('party.party', 'Student', domain=[('is_student', '=', True)], 
                              required=True,
                              depends=['year'])
    voucher_id = fields.Char('Voucher ID')
    payments = fields.One2Many('school.payment', 'payment_receipt', 'Payments')
    # receipt_report_cache = fields.Binary('Receipt Report', readonly=True)
    # receipt_report_format = fields.Char('Receipt Report Format', readonly=True)
    inscription = fields.Function(fields.Many2One('school.inscription', 'Inscription'), 'get_inscription')

    @staticmethod
    def default_date():
        return datetime.today()

    @classmethod
    def _new_code(cls, **pattern):
        pool = Pool()
        Configuration = pool.get('school.configuration')
        config = Configuration(1)
        sequence = config.payment_receipt_sequence
        if sequence:
            return sequence.get()

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if not values.get('code'):
                values['code'] = cls._new_code()
        return super(SchoolPaymentReceipt, cls).create(vlist)
    
    @classmethod
    def send_receip_notify(cls, receip):
        pool = Pool()
        ContactMechanism = pool.get('party.contact_mechanism')
        contact_mechanisms = ContactMechanism.search([('party', '=', receip.student), ('type', '=', 'email')])
        to = [contact_mechanism.value for contact_mechanism in contact_mechanisms]
        _send_email(None, to, cls.get_email_payment_notify, receip, cls.print_notify([receip]))

    @classmethod
    def get_email_payment_notify(self, receipt):
        pool = Pool()
        Language = pool.get('ir.lang')
        languages = Language.search([
            ('code', '=', Transaction().language),
            ])
        return get_email(
            'school.email.payment.notify.report', receipt, languages)

    @classmethod
    def print_notify(cls, receipts):
        res = []
        SchoolPaymentReceipt = Pool().get('school.payment.receipt', type='report')
        for receipt in receipts:
            res.append(SchoolPaymentReceipt.execute([receipt.id], {}))
        return res
    
    def total(self):
        res = 0
        for payment in self.payments:
            res += payment.amount_paid
        return res
    
    @classmethod
    def get_inscription(cls, records, name):
        pool = Pool()
        res = {}
        Inscription = pool.get('school.inscription')
        for record in records:
            inscription, = Inscription.search([('year', '=', record.year),('student', '=', record.student)])
            res[record.id] = inscription
        return res


class SchoolEmailPaymentNotifyReport(Report):
    __name__ = 'school.email.payment.notify.report'

    @classmethod
    def get_context(cls, records, header, data):
        context = super().get_context(records, header, data)
        return context
