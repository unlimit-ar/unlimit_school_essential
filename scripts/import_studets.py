#!/usr/bin/env python3
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import gettext
import os
import sys
from argparse import ArgumentParser
import datetime
import pycountry

try:
    from progressbar import ProgressBar, Bar, ETA, SimpleProgress
except ImportError:
    ProgressBar = None

try:
    from proteus import Model, config
except ImportError:
    prog = os.path.basename(sys.argv[0])
    sys.exit("proteus must be installed to use %s" % prog)


def find_student(file):
    import csv
    Party = Model.get('party.party')
    Country = Model.get('country.country')
    with open(file, newline='') as csvfile:
        students = csv.DictReader(csvfile)
        for row in students:
            party = Party()
            if row.get('dni', False):
                party.doc_number = row.get('dni')
                party.name = row.get('nombre').split(',')[0]
                party.lastname = row.get('nombre').split(',')[0]
                party.is_student = True
                party.is_person = True
                if row.get('sexo', False):
                    party.gender = 'men'
                else:
                    party.gender = 'women'
                if row.get('fecha_nacim'):
                    fecha_nacim = row.get('fecha_nacim')
                else:   
                    fecha_nacim = '01/01/99 00:00:00'
                party.dob = datetime.datetime.strptime(fecha_nacim, '%m/%d/%y %H:%M:%S').date()
            
                country_str = row.get('nacionalidad')[:3]
                country = Country.find([('name', 'ilike', country_str)])
                country2 = Country.find([('name', 'ilike', 'Argentina')])
                party.citizenship = country[0] if country else country2[0]
                party.save()
                address, = party.addresses
                street = ', '.join([row.get('calle', ''), row.get('barrio', '')])
                address.street = street
                address.city = row.get('localidad', '')
                address.save()
                if row.get('tele1', False):
                    party.contact_mechanisms.new(type='mobile', value=row.get('tele1', ''), name=row.get('dueño1', ''))
                if row.get('tele2', False):
                    party.contact_mechanisms.new(type='mobile', value=row.get('tele2', ''), name=row.get('dueño2', ''))
                party.save()

                
def main(database, config_file=None, file=None):
    config.set_trytond(database, config_file=config_file)
    with config.get_config().set_context(active_test=False):
        do_import(file)


def do_import(file):
    find_student(file)
    

def run():
    parser = ArgumentParser()
    parser.add_argument('-f', '--file', dest='file', required=True,
                        help="file get de student")
    parser.add_argument('-d', '--database', dest='database', required=True)
    parser.add_argument('-c', '--config', dest='config_file',
        help='the trytond config file')

    args = parser.parse_args()
    main(args.database, args.config_file, args.file)


if __name__ == '__main__':
    run()
