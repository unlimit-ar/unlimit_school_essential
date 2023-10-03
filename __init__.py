
from trytond.pool import Pool
from . import party
from . import school
from . import payment
from . import inscription

def register():
    Pool.register(
        party.Party,
        party.Family,
        school.SchoolLevel,
        school.SchoolLevelYear,
        school.SchoolProduct,
        school.SchoolProductLine,
        payment.SchoolPayment,
        payment.SchoolAccountStatusContext,
        payment.SchoolAccountStatus,
        inscription.SchoolInscription,
        module='unlimit_school_essential', type_='model')
    Pool.register(
        inscription.WizardSchoolInscription,
        module='unlimit_school_essential', type_='wizard')
    Pool.register(
        payment.SchoolPaymentReport,
        module='unlimit_school_essential', type_='report')
    
