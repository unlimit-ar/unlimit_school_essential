
from trytond.pool import Pool
from . import party
from . import school
from . import payment
from . import inscription
from . import configuration
from . import ir

def register():
    Pool.register(
        party.Party,
        party.Family,
        school.SchoolLevel,
        school.SchoolLevelYear,
        school.SchoolProduct,
        school.SchoolProductLine,
        school.SchoolNotifyStart,
        school.SchoolNotifyAttachment,
        school.SchoolDebtNotice,
        school.SchoolDebtCheckOrder,
        payment.SchoolPayment,
        payment.SchoolAccountStatusContext,
        payment.SchoolAccountStatus,
        payment.SchoolPaymentWizardStart,
        payment.SchoolPaymentReceipt,
        inscription.SchoolInscription,
        configuration.SchoolConfiguration,
        ir.Cron,
        module='unlimit_school_essential', type_='model')
    Pool.register(
        inscription.WizardSchoolInscription,
        payment.SchoolPaymentWizard,
        school.SchoolNotifyWizard,
        module='unlimit_school_essential', type_='wizard')
    Pool.register(
        payment.SchoolPaymentReceiptReport,
        payment.SchoolEmailPaymentNotifyReport,
        payment.SchoolPaymentReport,
        module='unlimit_school_essential', type_='report')
    
