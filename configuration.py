from trytond.model import ModelView, ModelSQL, ModelSingleton, fields
from trytond.pyson import Id
from datetime import datetime


class SchoolConfiguration(ModelSingleton, ModelSQL, ModelView): 
    "School Configuration" 
    __name__ = 'school.configuration' 

    payment_receipt_sequence = fields.Many2One('ir.sequence', 'Payment Receipt Sequence',
        domain=[
            ('sequence_type', '=', Id('unlimit_school_essential', 'sequence_type_payment_receipt')),
            ])
    limit_email = fields.Integer('Limit Email')
    sends_email = fields.Integer('Sends Email')
    date_email = fields.DateTime('Date')

    @staticmethod
    def default_limit_email():
        return 0   

    @staticmethod
    def default_sends_email():
        return 0

    @staticmethod
    def default_date_email():
        return datetime.now()
    
    def validation_emails(self, cant):
        today = datetime.now()
        if cant >= self.limit_email:
            return False
        delta = self.date_email - today
        if delta.days >= 1:
            self.sends_email = cant
            self.date_email = today
            self.save()
            return True
        elif self.sends_email + cant <= self.limit_email:
            self.sends_email =  self.sends_email + cant
            self.date_email = today
            self.save()
            return True
        return False
            