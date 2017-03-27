# -*- coding: utf-8 -*-

## see https://packaging.python.org/distributing/#setup-py

from setuptools import setup, find_packages
from codecs import open
from os import path
import sys

install_requires = ['six', 'easywebdav', 'pycrypt']

if sys.version_info[0] == 3: # Python 3
	install_requires.append('blowfish')


pwd = path.abspath(path.dirname(__file__))

setup(
	name = 'syncacre',
	version = '0.1',
	description = 'Syncacre - Client-to-client synchronization based on external relay storage',
	url = 'https://github.com/francoislaurent/syncacre',
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
