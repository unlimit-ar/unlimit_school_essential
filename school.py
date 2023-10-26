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


from trytond.model import DeactivableMixin, fields, Unique, ModelSQL, ModelView, Workflow, sequence_ordered
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
    lines = fields.One2Many('school.product.line', 'product', 'Line')
    total_amount = fields.Function(fields.Numeric('Total Amount'), 'on_change_with_total_amount')
    # amount = fields.Numeric('Amount', digits=(16,2))
    part = fields.Integer('Part', states={'invisible': Bool(Eval('share'))})
    currency = fields.Many2One('currency.currency', 'Currency')
    state = fields.Selection([
        (None, ''),
        ('paid', 'Paid'),
        ('must', 'Must')
        ], 'State')

    @classmethod
    def __setup__(cls):
        super(SchoolProduct, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints += [
            ('level_uniq', Unique(table, table.level, table.type),
                'unlimit_school_essential.msg_level_uniq')
        ]

    # def get_rec_name(self, name):
    #     if self.part:
    #         return str(self.part) + ' ' + self.product.rec_name
    #     return self.product.rec_name
    
    @fields.depends('lines')
    def on_change_with_total_amount(self, name=None):
        total_amount = Decimal('0')
        for line in self.lines:
            total_amount += line.amount
        return total_amount
    
    @classmethod
    def update_amount(cls, years):
        for year in years:
            school_products = cls.seach([('inscription.year', '=', year), ('state', '!=', 'paid')])
        import pdb;pdb.set_trace()
        pass

    @classmethod
    def write(cls, products, values, *args):
        super(SchoolProduct, cls).write(products, values, *args)
        Payment = Pool().get('school.payment')
        for product in products:
            payments = Payment.search([('product', '=', product.id), ('state', '=', 'must')])
            Payment.write(payments, {'amount_paid': product.total_amount})


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
            return '[' + self.shift_time + '] ' + self.name
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
    students = fields.Many2Many('school.inscription', None, None, 'Student', 
        domain=[
            ('student.is_student', '=', True),
            ('year', '=', Eval('year'))], 
        required=True)

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
        ContactMechanism = pool.get('party.contact_mechanism')
        students = [inscription.student for inscription in self.start.students]
        contact_mechanisms = ContactMechanism.search([('party', 'in', students), ('type', '=', 'email')])
        to = [contact_mechanism.value for contact_mechanism in contact_mechanisms]
        _send_email(None, to, self.start.subject, self.start.body, self.start.attachment)
        return 'end'