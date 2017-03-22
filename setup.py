# -*- coding: utf-8 -*-

## see https://packaging.python.org/distributing/#setup-py

from setuptools import setup, find_packages
from codecs import open
from os import path

install_requires = ['six', 'easywebdav']


pwd = path.abspath(path.dirname(__file__))

setup(
	name = 'across',
	version = '0.1',
	description = 'ACRosS - All Clients Relay Synchronizer',
	url = 'https://github.com/francoislaurent/across',
	author = 'François Laurent',
	author_email = 'francois.laurent1@protonmail.com',
	license = 'MIT',
	classifiers = [
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.5',
	],
	packages = find_packages(exclude=['doc']),
	install_requires = install_requires,
)
