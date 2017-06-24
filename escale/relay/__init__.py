# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent
#   Contribution: webdav and googledrive try block

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from .info import *
from .relay import AbstractRelay, Relay
from escale.base.exceptions import MissingSetupFeature

__all__ = ['LockInfo', 'parse_lock_file', 'AbstractRelay', 'Relay']


def _read__protocol__(module_name):
	import os
	pwd = os.path.abspath(os.path.dirname(__file__))
	module_path = os.path.join(pwd, module_name + '.py')
	with open(module_path, 'r') as f:
		while True:
			line = f.readline().lstrip()
			if line.startswith('__protocol__'):
				protocol = line.split('=')[1].strip()
				break
	return protocol.split("'")[1::2]


__protocols__ = []
__extra_protocols__ = {}
__multi_path_protocols__ = []


try:
	from .localmount import LocalMount # should never fail
except ImportError as e:
	print(e)
else:
	__all__.append('LocalMount')
	__protocols__.append(LocalMount)

try:
	from .ftp import FTP # should never fail
except ImportError as e:
	print(e)
else:
	__all__.append('FTP')
	__protocols__.append(FTP)

try:
	from .ssh import SSH
except ImportError:
	for _p in _read__protocol__('ssh'):
		__extra_protocols__[_p] = 'SSH'
else:
	__all__.append('SSH')
	__protocols__.append(SSH)

try:
	from .webdav import WebDAV
except ImportError:
	for _p in _read__protocol__('webdav'):
		__extra_protocols__[_p] = 'WebDAV'
else:
	__all__.append('WebDAV')
	__protocols__.append(WebDAV)

try:
	from .google import GoogleDrive # should never fail
except ImportError as e:
	print(e)
else:
	__all__.append('GoogleDrive')
	__protocols__.append(GoogleDrive)
	try:
		if GoogleDrive._is_multi_path:
			__multi_path_protocols__ += GoogleDrive.__protocol__
	except AttributeError as e:
		print(e)


def by_protocol(protocol):
	for p in __protocols__[::-1]:
		if isinstance(p.__protocol__, list):
			if protocol in p.__protocol__:
				return p
		elif protocol == p.__protocol__:
			return p
	try:
		extra_requires = __extra_protocols__[protocol]
	except KeyError:
		raise KeyError("cannot find protocol '{}'".format(protocol))
	else:
		raise MissingSetupFeature(extra_requires)


__all__ += ['__protocols__', '__extra_protocols__', 'by_protocol', '__multi_path_protocols__']
