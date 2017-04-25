# -*- coding: utf-8 -*-

## see https://packaging.python.org/distributing/#setup-py

from setuptools import setup
#from codecs import open
#from os import path
import sys
import syncacre

install_requires = []
extra_requires = {
	'WebDAV':	['easywebdav'],
# the SSH feature may not be introduced ever
#	'SSH':		['paramiko'],
	'Blowfish':	['cryptography'],
	'Fernet':	['cryptography']}

if sys.version_info[0] == 3: # Python 3
	try:
		import blowfish
		extra_requires['Blowfish'] = []
		# Since `blowfish` is already available, the `cryptography` dependency is removed.
		# However, if `cryptography` is eventually available and 'Blowfish' requested,
		# `cryptography` may prevail instead of `blowfish` (or not).
		# See `syncacre.cryptography.blowfish` for more information.
	except ImportError:
		pass


#pwd = path.abspath(path.dirname(__file__))

setup(
	name = 'syncacre',
	version = syncacre.__version__,
	description = 'SynCÀCRe - Client-to-client synchronization based on external relay storage',
	url = 'https://github.com/francoislaurent/syncacre',
	author = 'François Laurent',
	author_email = 'francois.laurent1@protonmail.com',
	license = 'ISC',
	classifiers = [
		'Environment :: No Input/Output (Daemon)',
		'Intended Audience :: End Users/Desktop',
		'Intended Audience :: Science/Research',
		'Intended Audience :: Developers',
		'Operating System :: MacOS :: MacOS X',
		'Operating System :: POSIX :: Linux',
		'Operating System :: Unix',
		'Topic :: Communications :: File Sharing',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.5',
	],
	packages = ['syncacre'],
	install_requires = install_requires,
	extra_requires = extra_requires,
)

