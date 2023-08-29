#!/usr/bin/env python
# encoding: utf-8
#This file is part sale_pos module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.

from setuptools import setup
import re
import os
import io
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

MODULE = 'unlimit_school_essential'
PREFIX = ''
MODULE2PREFIX = {
    }


def read(fname):
    return io.open(
        os.path.join(os.path.dirname(__file__), fname),
        'r', encoding='utf-8').read()


def get_require_version(name):
    require = '%s >= %s.%s, < %s.%s'
    require %= (name, major_version, minor_version,
        major_version, minor_version + 1)
    return require


config = ConfigParser()
config.readfp(open('tryton.cfg'))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()

version = info.get('version', '0.0.1')
major_version, minor_version, _ = version.split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)

requires = ['appdirs', 'Babel', 'Click', 'formulas', 'Jinja2',
    'openpyxl', 'matplotlib', 'pandas', 'psycopg2', 'PyPDF2', 
    'pytz', 'unidecode', 'WeasyPrint', 'werkzeug', 'xlrd', 'xlutils']

for dep in info.get('depends', []):
    if re.match(r'^unlimit*', dep):
        continue
    if re.search(r'_ar$', dep):
        continue
    if not re.match(r'(ir|res)(\W|$)', dep):
        prefix = MODULE2PREFIX.get(dep, 'trytond')
        requires.append(get_require_version('%s_%s' % (prefix, dep)))

requires.append(get_require_version('trytond'))
requires.append(get_require_version('proteus'))
tests_require = [get_require_version('proteus')]

tests_require = []

setup(name=MODULE,
    
    version=version,
    description='School Essential',
    author='unlimit.ar',
    url='http://unlimit.ar',
    download_url="",
    package_dir={'trytond.modules.%s' % MODULE: '.'},
    packages=[
        'trytond.modules.%s' % MODULE,
        ],
    package_data={
        'trytond.modules.%s' % MODULE: (info.get('xml', []) +
            ['tryton.cfg', 'view/*.xml',
                'locale/*.po', 'locale/override/*.po', 'report/*.fodt',
                'report/*.fods', 'report/*.html', 'report/stylesheet/*.css',
                'report/translations/*/*/*.po', 'icons/*.svg', 'tests/*.rst']),
        },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: Bulgarian',
        'Natural Language :: Catalan',
        'Natural Language :: Czech',
        'Natural Language :: Dutch',
        'Natural Language :: English',
        'Natural Language :: French',
        'Natural Language :: German',
        'Natural Language :: Russian',
        'Natural Language :: Spanish',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Office/Business',
        ],
    license='GPL-3',
    install_requires=requires,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    %s = trytond.modules.%s
    """ % (MODULE, MODULE),
    test_suite='tests',
    test_loader='trytond.test_loader:Loader',
    tests_require=tests_require,
    )
