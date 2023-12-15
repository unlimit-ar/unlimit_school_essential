import re
import pytz
from datetime import datetime
from sql import Literal
import calendar
import mimetypes
from decimal import Decimal
from unittest.mock import ANY, Mock, patch
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.nonmultipart import MIMENonMultipart
from email.encoders import encode_base64
from dateutil.relativedelta import relativedelta
from itertools import chain, groupby, islice, product, repeat

from trytond.model import DeactivableMixin, fields, Unique, ModelSQL, ModelView, Workflow, sequence_ordered, ModelSingleton
from trytond.wizard import Wizard, Button, StateView, StateTransition
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Or, Id
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.sendmail import sendmail_transactional
from trytond.tools.email_ import set_from_header
from trytond.config import config
from trytond.i18n import gettext


def _send_email(from_, to, title, body, attachments=[]):
    
    files = [
        (a.name, a.data) for a in attachments]

    msg = MIMEMultipart('alternative')
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

    msg.attach(MIMEText(body, 'html', _charset='utf-8'))
    msg.add_header('Content-Language', ', '.join(Transaction().context.get('language')))
    from_cfg = config.get('email', 'from')
    set_from_header(msg, from_cfg, from_ or from_cfg)
    msg['bcc'] = ', '.join(to)
    msg['Subject'] = Header(title, 'utf-8')

    sendmail_transactional(from_cfg, to, msg)


class SchoolProduct(ModelSQL, ModelView):
    'School Product'
    __name__ = 'school.product'

    type = fields.Selection([
            ('inscription', 'Inscription'),
            ('share', 'Share')
        ], 'Type')
    type_string = type.translated('type')
    level = fields.Many2One('school.level', 'Level')
    lines = fields.One2Many('school.product.line', 'product', 'Line', size=9)
    total_amount = fields.Function(fields.Numeric('Total Amount'), 'on_change_with_total_amount')
    # amount = fields.Numeric('Amount', digits=(16,2))
    part = fields.Integer('Part', states={'invisible': Bool(Eval('share'))})
    currency = fields.Many2One('currency.currency', 'Currency')
    state = fields.Selection([
        (None, ''),
        ('paid', 'Paid'),
        ('must', 'Must')
        ], 'State')
    paid = fields.Boolean('Paid')

    # @classmethod
    # def __setup__(cls):
    #     super(SchoolProduct, cls).__setup__()
    #     table = cls.__table__()
    #     cls._sql_constraints += [
    #         ('level_uniq', Unique(table, table.level, table.type),
    #             'unlimit_school_essential.msg_level_uniq')
    #     ]

    # def get_rec_name(self, name):
    #     if self.part:
    #         return str(self.part) + ' ' + self.product.rec_name
    #     return self.product.rec_name
    
    @fields.depends('lines')
    def on_change_with_total_amount(self, name=None):
        return self.amount_with_extra_products([])
        
    @classmethod
    def write(cls, products, values, *args):
        super(SchoolProduct, cls).write(products, values, *args)
        Payment = Pool().get('school.payment')
        for product in products:
            #TODO Revisar en la incripcion las materias extra.
            payments = Payment.search([('product', '=', product.id), ('state', '=', 'must')])
            Payment.__queue__.update_ammount(payments)


    # @classmethod
    # def write(cls, products, values, *args):
    #     args2 = list(args)
    #     sps = []
    #     actions = iter((products, values) + args)
    #     if products:
    #         for records, values2 in zip(actions, actions):
    #             year = getattr(products[0], 'year', None)
    #             sps = cls.search([('inscription.year', '=', year), ('state', '=', 'must'), ('product', 'in', [p.product for p in records])])
    #             args2.append(sps)
    #             args2.append(values2)
    #     super(SchoolProduct, cls).write(products, values, *args2)

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.id
        
    @staticmethod
    def default_part():
        return 1
    
    @staticmethod
    def default_share():
        return 'share'
    
    @staticmethod
    def default_paid():
        return False
    
    def amount_with_extra_products(self, extras=[]):
        total = Decimal(0)
        pool = Pool()
        ExtraProduct = pool.get('school.extra.product')
        extra_products = [e.name for e in ExtraProduct.search([])]
        for line in self.lines:
            if line.name in extra_products:
                if line.name in extras:
                    total += line.amount
            else:
                total += line.amount
        return total
    

class SchoolProductLine(ModelSQL, ModelView):
    'School Product Line'
    __name__ = 'school.product.line'

    product = fields.Many2One('school.product', 'Product')
    name = fields.Char('Name', required=True)
    amount = fields.Numeric('Amount', digits=(16,2), required=True)

    def default_amount():
        return '0'


class SchoolLevel(ModelSQL, ModelView):
    'School Level'
    __name__ = 'school.level'

    name = fields.Char('Name')
    year = fields.One2Many('school.level.year', 'level', 'Year')


class SchoolLevelYear(ModelSQL, ModelView):
    'School Level Year'
    __name__ = 'school.level.year'

    name = fields.Char('Name', states={'required': True})
    level = fields.Many2One('school.level', 'Level')
    shift_time = fields.Selection([
            (None, ''),
            ('TT', 'TT'),
            ('TM', 'TM')
        ], 'Shift Time')
    
    def get_rec_name(self, name):
        if self.shift_time:
            return '[' + self.level.name + ' - ' + self.shift_time + '] ' + self.name
        return self.name
    

class SchoolNotifyAttachment(ModelView):
    "Attachment"
    __name__ = 'school.notify.attachment'

    name = fields.Char('Name')
    data = fields.Binary('Data', filename='name')


class SchoolNotifyStart(ModelView):
    'School Notify'
    __name__ = 'school.notify.start'

    year = fields.Integer('Year')
    subject = fields.Char("Subject", required=True)
    body = fields.Text("Body", required=True)
    attachment = fields.One2Many('school.notify.attachment', None, 'Attachment')
    # students = fields.Many2Many('party.party', None, None, 'Student', domain=[('is_student', '=', True)], 
    #                         required=True)
    students = fields.Many2Many('school.inscription', None, None, 'Student', size=Eval('students_size', 0),
        domain=[
            ('student.is_student', '=', True),
            ('year', '=', Eval('year'))], 
        required=True, depends=['students_size'])
    students_size = fields.Integer('students_size')

    @staticmethod
    def default_year():
        return datetime.today().year
    

class SchoolNotifyWizard(Wizard):
    'School Notify Wizard'
    __name__ = 'school.notify.wizard'

    start = StateView('school.notify.start',
        'unlimit_school_essential.school_notify_start_form_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Send E-Mail', 'send', 'tryton-ok', default=True),
            ])

    send = StateTransition()

    def transition_send(self):
        pool = Pool()
        config = pool.get('school.configuration')(1)
        ContactMechanism = pool.get('party.contact_mechanism')
        students = [inscription.student for inscription in self.start.students]
        contact_mechanisms = ContactMechanism.search([('party', 'in', students), ('type', '=', 'email')])
        to = [contact_mechanism.value for contact_mechanism in contact_mechanisms]
        config.validation_emails(len(to))
        
        _send_email(None, to, self.start.subject, self.start.body, self.start.attachment)
        return 'end'

    def default_start(self, fields):
        pool = Pool()
        config = pool.get('school.configuration')(1)
        size = config.limit_email - config.sends_email -50
        return {'students_size': size if size > 0 else 0}


class SchoolDebtNotice(ModelSingleton, ModelSQL, ModelView):
    'School Debt Notice'
    __name__ = 'school.debt.notice'

    subject = fields.Char("Subject", required=True)
    body = fields.Text("Body", required=True)
    check_orders = fields.One2Many('school.debt.check.order', 'debt_notice', 'Order')

    @classmethod
    def colect_debts(cls):
        date = datetime.today()
        debt_notice = cls(1)
        for check_order in debt_notice.check_orders:
            if check_order.date_number == date.day:
                for party_id, in cls.get_student_debts():
                    cls.send_debts_notify(party_id)
        pass

    @classmethod
    def get_student_debts(cls):
        students = []
        cursor = Transaction().connection.cursor()
        cursor.execute("""
            select party_party.id
            from party_party
            join school_inscription ON school_inscription.student = party_party.id
            join school_payment on school_payment.inscription = school_inscription.id
            where school_payment.state = 'must'
            group by 1""")
    
        students.append(cursor.fetchall())
        students = list(chain(*students))
        return students
    
    @classmethod
    def send_debts_notify(cls, party_id):
        pool = Pool()
        
        party = pool.get('party.party')(party_id)
        ContactMechanism = pool.get('party.contact_mechanism')
        contact_mechanisms = ContactMechanism.search([('party', '=', party_id), ('type', '=', 'email')])
        to = [contact_mechanism.value for contact_mechanism in contact_mechanisms]
        config = pool.get('school.configuration')(1)
        config.validation_emails(len(to))

        debt_notice = pool.get('school.debt.notice')(1)
        SchoolPayment = pool.get('school.payment')
        date = datetime.today().date() - relativedelta(months=1)

        payments_must = SchoolPayment.search([('student', '=', party_id), ('state', '=', 'must'), ('date', '<', date)])
        # payment_inscription = SchoolPayment.search([('student', '=', party_id), ('state', '=', 'must'), ('type', '=', 'inscription')])
        must_names = ', '.join([share.name for share in payments_must])
        # inscription_names = ', '.join([share.name for share in payment_inscription])

        _send_email(None, to, debt_notice.subject, debt_notice.body.format(a=party.name, b=party.lastname, c=must_names))
        


class SchoolDebtCheckOrder(ModelSQL, ModelView):
    'School Debt Check Order'
    __name__ = 'school.debt.check.order'

    level = fields.Many2One('school.level', 'Level')
    date_number = fields.Integer('Date Number')
    debt_notice = fields.Many2One('school.debt.notice', 'Debt Notice')

    @classmethod
    def __setup__(cls):
        super(SchoolDebtCheckOrder, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints += [
            ('level_uniq', Unique(table, table.level),
                'unlimit_school_essential.msg_level_uniq')
        ]


class SchoolExtraProduct(ModelSQL, ModelView):
    'School Extra Product'
    __name__ = 'school.extra.product'

    name = fields.Char('Name')