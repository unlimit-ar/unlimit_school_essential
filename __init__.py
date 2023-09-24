
from trytond.pool import Pool
from . import party
from . import school

def register():
    Pool.register(
        party.Party,
        school.SchoolLevel,
        school.SchoolLevelYear,
        school.SchoolProduct,
        school.SchoolProductLine,
        module='unlimit_school_essential', type_='model')
    Pool.register(
        module='unlimit_school_essential', type_='wizard')
    Pool.register(
        module='unlimit_school_essential', type_='report')
    
