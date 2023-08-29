
from trytond.pool import Pool
from . import party
from . import school
from . import payment
from . import configuration

def register():
    Pool.register(
        party.Party,
        party.Family,
        party.FamilyMember,
        school.SchoolFeeType,
        school.SchoolGrade,
        school.SchoolLevel,
        school.SchoolProduct,
        school.SchoolSection,
        school.SchoolYearSchoolProduct,
        school.SchoolYear,
        school.SchoolConfigStart,
        school.SchoolInscription,
        payment.SchoolPayment,
        payment.SchoolPaymentIncome,
        configuration.SchoolProductsConfiguration,
        configuration.Configuration,
        module='unlimit_school_essential', type_='model')
    Pool.register(
        school.SchoolConfig,
        school.SchoolInscriptionStudent,
        module='unlimit_school_essential', type_='wizard')
    Pool.register(
        payment.SchoolPaymentReport,
        module='unlimit_school_essential', type_='report')
    
