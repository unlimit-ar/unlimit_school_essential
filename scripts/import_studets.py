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

import pandas as pd

alumnos = '/home/pablo/Descargas/db_escuela/alumno.csv'
padres = '/home/pablo/Descargas/db_escuela/padres.csv'
padres_csv = pd.read_csv(padres)

def get_citizenship(nacionalidad):
    Country = Model.get('country.country')
    country_str = nacionalidad
    country = []
    if country_str:
        country = Country.find([('name', 'ilike', country_str)])
    country2 = Country.find([('name', 'ilike', 'Argentina')])
    return country[0] if country else country2[0]

def find_student(file):
    import csv
    Party = Model.get('party.party')
    Family = Model.get('party.family')
    Country = Model.get('country.country')
    with open(file, newline='') as csvfile:
        students = csv.DictReader(csvfile)
        for row in students:
            party = Party()
            
            if row.get('dni', False):
                partys = Party.find([('doc_number', '=', row.get('dni'))])
                if partys:
                    party = partys[0]
                    party.is_student = True
                    if row.get('sexo', False):
                        party.gender = 'men'
                    else:
                        party.gender = 'women'
                    if row.get('fecha_nacim'):
                        fecha_nacim = row.get('fecha_nacim')
                    else:   
                        fecha_nacim = '01/01/99 00:00:00'
                    party.dob = datetime.datetime.strptime(fecha_nacim, '%m/%d/%y %H:%M:%S').date()
                    address, = party.addresses
                    street = ', '.join([row.get('calle', ''), row.get('barrio', '')])
                    address.street = street
                    address.city = row.get('localidad', '')
                    address.save()
                    if row.get('tele1', False):
                        party.contact_mechanisms.new(type='mobile', value=row.get('tele1', ''), name=row.get('dueño1', ''))
                    if row.get('tele2', False):
                        party.contact_mechanisms.new(type='mobile', value=row.get('tele2', ''), name=row.get('dueño2', ''))
                else:
                    party.doc_number = row.get('dni')
                    nombres = row.get('nombre').split(',')
                    if len(nombres) == 1:
                        nombres = row.get('nombre').split(' ')
                    party.name = ' '.join(nombres[1:] or nombres)
                    party.lastname = nombres[0]

                    # party.name = row.get('nombre').split(',')[0]
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
                    
                    # country = Country.find([('name', 'ilike', country_str)])
                    # country2 = Country.find([('name', 'ilike', 'Argentina')])
                    # party.citizenship = country[0] if country else country2[0]
                    party.citizenship = get_citizenship(country_str)
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
                    # Padres
                    cod_padre = row.get('cod_padre')
                    if cod_padre:
                        parent_party = Party.find([('doc_number', '=', cod_padre)])
                        if not parent_party:
                            parent_party = Party()
                            row_padre = padres_csv.loc[padres_csv['dni']==int(cod_padre)]
                            if not row_padre.empty:
                                parent_party.doc_number = cod_padre
                                nombres = row_padre.nombre.values[0].split(',')
                                if len(nombres) == 1:
                                    nombres = row_padre.nombre.values[0].split(' ')
                                parent_party.name = ' '.join(nombres[1:] or nombres)
                                parent_party.lastname = nombres[0] or nombres[1] 
                            country_str = row_padre.nacionalidad.values[0]
                            parent_party.citizenship = get_citizenship(country_str)
                            
                            if not row_padre.ocupación.isnull:
                                parent_party.employment = row_padre.ocupación.values[0]
                            else:
                                parent_party.employment = 'None'

                            if not row_padre.estudios.isnull:
                                parent_party.studies = row_padre.estudios.values[0]
                            else:
                                parent_party.studies = 'None'

                            parent_party.is_person = True    
                            parent_party.save()
                        else:
                            parent_party = parent_party[0]
                        family = Family()
                        family.party = party
                        family.parent = parent_party
                        family.save()

                
                party.save()
                
def main(database, config_file=None, file=None):
    config.set_trytond(database, config_file=config_file)
    with config.get_config().set_context(active_test=False):
        if not file:
            file = alumnos
        do_import(file)


def do_import(file):
    find_student(file)
    

def run():
    parser = ArgumentParser()
    parser.add_argument('-f', '--file', dest='file',
                        help="file get de student")
    parser.add_argument('-d', '--database', dest='database', required=True)
    parser.add_argument('-c', '--config', dest='config_file',
        help='the trytond config file')

    args = parser.parse_args()
    main(args.database, args.config_file, args.file)


if __name__ == '__main__':
    run()
