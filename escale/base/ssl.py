# -*- coding: utf-8 -*-

# Copyright (c) 2017, Institut Pasteur
#        Contributor: François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from __future__ import absolute_import

from .essential import *
import ssl

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager


_ssl_symbol = {
		'sslv2':	'SSLv2',
		'sslv3':	'SSLv3',
		'sslv23':	'SSLv23',
		'tls':	'TLS',
		'tlsv1':	'TLSv1',
		'tlsv1.1':	'TLSv1_1',
		'tlsv1.2':	'TLSv1_2',
	}


_ssl_version = {}
try:
	_ssl_version['sslv2'] = ssl.PROTOCOL_SSLv2
except AttributeError:
	pass
try:
	_ssl_version['sslv3'] = ssl.PROTOCOL_SSLv3
except AttributeError:
	pass
try:
	_ssl_version['sslv23'] = ssl.PROTOCOL_SSLv23 # SSLv23 is supposed to be an alias for TLS
except AttributeError:
	pass
try:
	_ssl_version['tls'] = ssl.PROTOCOL_TLS
except AttributeError:
	try:
		_ssl_version['tls'] = ssl.PROTOCOL_SSLv23
	except AttributeError:
		pass

default_ssl_context = None

if 'tls' in _ssl_version:
	default_ssl_context = ssl.SSLContext(_ssl_version['tls'])
	_default_options = default_ssl_context.options
	try:
		default_ssl_context.options |= ssl.OP_NO_SSLv2
	except AttributeError:
		pass
	try:
		default_ssl_context.options |= ssl.OP_NO_SSLv3
	except AttributeError:
		pass
	if default_ssl_context.options != _default_options:
		_ssl_version['tls'] = default_ssl_context

try:
	_ssl_version['tlsv1'] = ssl.PROTOCOL_TLSv1
except AttributeError:
	pass
try:
	_ssl_version['tlsv1.1'] = ssl.PROTOCOL_TLSv1_1 # deprecated in OpenSSL 1.0.1
except AttributeError:
	pass
try:
	_ssl_version['tlsv1.2'] = ssl.PROTOCOL_TLSv1_2 # deprecated in OpenSSL 1.0.1
except AttributeError:
	pass


def parse_ssl_version(ssl_version):
	"""
	Parse SSL version.

	.. note:: support for 'SSLv2' and 'SSLv3' has been dropped by the standard `ssl` module and 
		these values will be translated to 'SSLv23'.

	Arguments:

		ssl_version (int or str): either any of ``ssl.PROTOCOL_*`` or any of 'SSLv2', 'SSLv3', 
			'SSLv23', 'TLS' (recommended), 'TLSv1', 'TLSv1.1' or 'TLSv1.2'.

	Returns:

		int or ssl.SSLContext: one of ``ssl.PROTOCOL_*`` codes or an SSLContext with modified options.

	"""
	if ssl_version is None:
		ssl_version = default_ssl_context
	elif isinstance(ssl_version, str) or (PYTHON_VERSION==2 and isinstance(ssl_version, unicode)):
		try:
			ssl_version = _ssl_version[ssl_version.lower()]
		except KeyError:
			raise AttributeError("the 'ssl' module has no symbol 'PROTOCOL_{}'".format(_ssl_symbol[ssl_version.lower()]))
	return ssl_version


def make_https_adapter(ssl_version_or_context):
	"""
	Make a `HTTPSAdapter` class that inheritates from :class:`~requests.adapters.HTTPAdapter`
	and forces a specific SSL version.

	Arguments:

		ssl_version_or_context (int or ssl.SSLContext): any of ``ssl.PROTOCOL_*`` codes 
			or an :class:`~ssl.SSLContext`.

	Returns:

		HTTPSAdapter: class, child of :class:`~requests.adapters.HTTPAdapter`.
	"""
	if isinstance(ssl_version_or_context, ssl.SSLContext):
		ssl_arg = dict(ssl_context=ssl_version_or_context)
	else:
		ssl_arg = dict(ssl_version=ssl_version_or_context)
	class HTTPSAdapter(HTTPAdapter):
		def init_poolmanager(self, connections, maxsize, block=False, **pool_args):
			self._pool_connections = connections
			self._pool_maxsize = maxsize
			self._pool_block = block
			pool_args.update(ssl_arg)
			self.poolmanager = PoolManager(
				num_pools=connections, maxsize=maxsize, block=block,
				**pool_args)
	return HTTPSAdapter

