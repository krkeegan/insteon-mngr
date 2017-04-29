#!/usr/bin/env python

from setuptools import setup
import sys

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except:
    print('Skipping md->rst conversion for long_description')
    long_description = 'Error converting Markdown from git repo'

if len(long_description) < 100:
    print("\n***\n***\nWARNING: %s\n***\n***\n" % long_description)

setup(
    name='insteon_mngr',
    version='0.0.1',
    author='Kevin Robert Keegan',
    author_email='kevin@krkeegan.com',
    url='https://github.com/krkeegan/insteon',
    license="LICENSE",
    packages=['insteon_mngr'],
    scripts=[],
    description='Python API for managing and controlling Insteon devices',
    long_description=long_description,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    include_package_data=True,
    zip_safe=True,
    install_requires=[
        'bottle>=0.12'
    ],
    entry_points={
    }
)
