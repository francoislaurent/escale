#!/usr/bin/env python
# -*- coding: utf-8 -*-

## see https://packaging.python.org/distributing/#setup-py

from setuptools import setup
import os
import sys
import codecs
from escale import PROGRAM_NAME, __version__

install_requires = ['requests', 'python-daemon']
extras_require = {
	'WebDAV':	['requests', 'pyopenssl'],
#	'SSH':		['paramiko'],
	'Blowfish':	['cryptography'],
	'Fernet':	['cryptography']}

if sys.version_info[0] == 3: # Python 3
	try:
		import blowfish
	except ImportError:
		pass
	else:
		extras_require['Blowfish'] = []
		# Since `blowfish` is already available, the `cryptography` dependency is removed.
		# However, if `cryptography` is eventually available and 'Blowfish' requested,
		# `cryptography` may prevail instead of `blowfish` (or not).
		# See `escale.cryptography.blowfish` for more information.


pwd = os.path.abspath(os.path.dirname(__file__))
readme = os.path.join(pwd, 'README.rst')
try:
	with codecs.open(readme, 'r', encoding='utf-8') as f:
		long_description = f.read()
except Exception as e:
	print(e)
	long_description = ''


setup(
	name = PROGRAM_NAME,
	version = __version__,
	description = 'Escale - Client-to-client synchronization based on external relay storage',
	long_description = long_description,
	url = 'https://github.com/francoislaurent/escale',
	author = 'François Laurent',
	author_email = 'francois.laurent1@protonmail.com',
	license = 'CeCILL-C',
	classifiers = [
		'License :: OSI Approved :: CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)',
		'Environment :: No Input/Output (Daemon)',
		'Intended Audience :: End Users/Desktop',
		'Intended Audience :: Science/Research',
		'Operating System :: MacOS :: MacOS X',
		'Operating System :: POSIX :: Linux',
		'Operating System :: Unix',
		'Topic :: Communications :: File Sharing',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.5',
		'Programming Language :: Python :: 3.6',
	],
	package_dir = {'syncacre': PROGRAM_NAME},
	packages = ['syncacre', PROGRAM_NAME] + \
		[ PROGRAM_NAME+'.'+module for module in [ \
			'base',
			'manager',
			'relay',
			'relay.webdav',
			'relay.google',
			'relay.generic',
			'log',
			'encryption',
			'cli',
			'cli.config',
			'oauth',
		] ],
	scripts = ['scripts/escale', 'scripts/escalectl'],
	install_requires = install_requires,
	extras_require = extras_require,
)

