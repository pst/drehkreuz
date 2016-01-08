#!/usr/bin/env python

from setuptools import setup

setup(
    name='BER',
    version='0.1.7',
    description='BER content aggregation hub',
    author='Philipp Strube',
    author_email='pst@cloudcontrol.de',
    url='',
    packages=['BER'],
    install_requires=[
        "tornado==4.0.2",
        "PyYAML==3.11",
        "Jinja2==2.7.3",
        "webassets==0.11.1",
        "libsass<0.10",
        "feedparser==5.2.1",
    ]
)
