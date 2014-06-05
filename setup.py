# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='fixity_checker',
    description='Yet another fixity checker',
    long_description=read('README.md'),
    version='0.1.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
    ],
    maintainer="Brian Tingle",
    maintainer_email='brian.tingle.cdlib.org@gmail.com',
    packages=find_packages(),
    install_requires=['shove', 'appdirs', 'psutil'],
    url='https://github.com/tingletech/fixity',
    py_modules=['fixity_checker', ],
    entry_points={
        'console_scripts': [
            'checker = fixity_checker:main',
            ''.join([
                'fixity_checker_report = ',
                'fixity_checker:fixity_checker_report_command',
            ])
        ]
    },
    test_suite='test',
)
