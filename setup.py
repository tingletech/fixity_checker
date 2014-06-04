# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

description = \
"""
Yet another fixity checker
"""

# for older pythons ...
requirements = []
try:
    import hashlib
except:
    requirements.append("hashlib")

requirements.append("shove")
requirements.append("appdirs")
requirements.append("psutil")

setup(
    name = 'fixity_checker',
    version= '0.1.0',
    maintainer = "Brian Tingle",
    maintainer_email = 'brian.tingle.cdlib.org@gmail.com',
    packages = find_packages(),
    install_requires = requirements,
    url = 'https://github.com/tingletech/fixity',
    py_modules = ['fixity_checker',],
    entry_points = {
        'console_scripts': [
            'checker = fixity_checker:main',
            'fixity_checker_report = fixity_checker:fixity_checker_report_command',
        ]
    },
    description = description,
    test_suite = 'test',
)
