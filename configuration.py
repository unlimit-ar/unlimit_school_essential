from trytond.model import ModelView, ModelSQL, ModelSingleton, fields
from trytond.pyson import Id


class SchoolConfiguration(ModelSingleton, ModelSQL, ModelView): 
    "School Configuration" 
    __name__ = 'school.configuration' 

    payment_receipt_sequence = fields.Many2One('ir.sequence', 'Payment Receipt Sequence',
        domain=[
            ('sequence_type', '=', Id('unlimit_school_essential', 'sequence_type_payment_receipt')),
            ])
    