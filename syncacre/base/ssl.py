from __future__ import absolute_import

from .essential import *
import ssl

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager


_ssl_symbol = {
	'sslv2':	'SSLv2',
	'sslv3':	'SSLv3',
	'sslv23':	'SSLv23',
	'tlsv1':	'TLSv1',
	'tlsv1.1':	'TLSv1_1',
	'tlsv1.2':	'TLSv1_2'}

_ssl_version = {}
try:
	_ssl_version['sslv2'] = ssl.PROTOCOL_SSLv2
except AttributeError:
	_ssl_version['sslv2'] = ssl.PROTOCOL_SSLv23
try:
	_ssl_version['sslv3'] = ssl.PROTOCOL_SSLv3
except AttributeError:
	_ssl_version['sslv3'] = ssl.PROTOCOL_SSLv23
_ssl_version['sslv23'] = ssl.PROTOCOL_SSLv23
try:
	_ssl_version['tlsv1'] = ssl.PROTOCOL_TLSv1
except AttributeError:
	pass
try:
	_ssl_version['tlsv1.1'] = ssl.PROTOCOL_TLSv1_1
except AttributeError:
	pass
try:
	_ssl_version['tlsv1.2'] = ssl.PROTOCOL_TLSv1_2
except AttributeError:
	pass


def parse_ssl_version(ssl_version):
	"""
	Parse SSL version.

	.. note:: support for 'SSLv2' and 'SSLv3' has been dropped and these values will be translated 
		to 'SSLv23'.

	Arguments:

		ssl_version (int or str): either any of ``ssl.PROTOCOL_*`` or any of 'SSLv2', 'SSLv3', 
			'SSLv23', 'TLSv1', 'TLSv1.1' or 'TLSv1.2'.

	Returns:

		int: one of ``ssl.PROTOCOL_*`` codes.

	"""
	if isinstance(ssl_version, str) or (PYTHON_VERSION==2 and isinstance(ssl_version, unicode)):
		try:
			ssl_version = _ssl_version[ssl_version.lower()]
		except KeyError:
			raise AttributeError("the 'ssl' module has no symbol 'PROTOCOL_{}'".format(_ssl_symbol[ssl_version.lower()]))
	return ssl_version


def make_https_adapter(ssl_version):
	"""
	Make a `HTTPSAdapter` class that inheritates from :class:`~requests.adapters.HTTPAdapter`
	and forces a specific SSL version.

	Arguments:

		ssl_version (int): any of ``ssl.PROTOCOL_*`` codes.

	Returns:

		HTTPSAdapter: class, child of :class:`~requests.adapters.HTTPAdapter`.
	"""
	class HTTPSAdapter(HTTPAdapter):
		def init_poolmanager(self, connections, maxsize, block=False):
			self.poolmanager = PoolManager(
				num_pools=connections, maxsize=maxsize,
				block=block, ssl_version=ssl_version)
	return HTTPSAdapter

