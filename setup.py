# -*- coding: utf-8 -*-

## see https://packaging.python.org/distributing/#setup-py

from setuptools import setup, find_packages
from codecs import open
from os import path
import sys

install_requires = ['easywebdav']
extra_requires = {}

if sys.version_info[0] == 3: # Python 3
	#extra_requires['Blowfish'] = ['blowfish']
	#extra_requires['AES'] = ['pycrypt']
	pass
else:
	#extra_requires['Blowfish'] = ['pycrypto']
	#extra_requires['AES'] = ['pycrypto']
	pass


#pwd = path.abspath(path.dirname(__file__))

setup(
	name = 'syncacre',
	version = '0.2',
	description = 'SynCÀCRe - Client-to-client synchronization based on external relay storage',
	url = 'https://github.com/francoislaurent/syncacre',
	author = 'François Laurent',
	author_email = 'francois.laurent1@protonmail.com',
	license = 'ISC',
	classifiers = [
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.5',
	],
	packages = find_packages(exclude=['doc']),
	install_requires = install_requires,
	extra_requires = extra_requires,
)

