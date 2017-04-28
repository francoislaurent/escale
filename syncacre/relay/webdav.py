# -*- coding: utf-8 -*-

# Copyright (c) 2017, Institut Pasteur
#   Contributor: François Laurent

from syncacre.base.essential import *
from syncacre.base.timer import *
from syncacre.base.ssl import *
from syncacre.log import log_root
from .relay import Relay

try:
	from urllib import quote, unquote # Py2
except ImportError:
	from urllib.parse import quote, unquote # Py3
import easywebdav
import requests
import os
import sys
import time
import itertools


# the following fix has been suggested in
# http://www.rfk.id.au/blog/entry/preparing-pyenchant-for-python-3/
if PYTHON_VERSION == 3:
	basestring = (str, bytes)
else:
	basestring = basestring


def _easywebdav_adapter(fun, mode, local_path_or_fileobj, *args):
	"""
	This code is partly borrowed from:
	https://github.com/amnong/easywebdav/blob/master/easywebdav/client.py

	Below follows the copyright notice of the easywebdav project which is supposed to be distibuted
	under the ISC license:
	::

		Copyright (c) 2012 year, Amnon Grossman

		Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

		THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

	"""
	if isinstance(local_path_or_fileobj, basestring):
		with open(local_path_or_fileobj, mode) as f:
			fun(f, *args)
	else:
		fun(local_path_or_fileobj, *args)


class WebDAVClient(easywebdav.Client):
	"""
	This class overwrites several of the methods of its parent class so that some errors are better
	documented, connection errors are handled and a Python3 bug is fixed.

	Attributes:

		retry_after (int): interval time in seconds before trying again.

		max_retry (int): number of retries after connection errors.

		timeout (int): maximum cumulated waiting time in seconds.

		url (str): full url of the remote repository; may appear in logs.

		ssl_version (int): any of the ``ssl.PROTOCOL_*`` constants.
	"""
	def __init__(self, host, retry_after=10, max_retry=None, timeout=None, url='', ssl_version=None, logger=None, \
		**kwargs):
		if logger is None:
			logger = logging.getLogger(log_root).getChild('WebDAVClient')
		self.logger = logger
		if 'path' in kwargs:
			kwargs['path'] = quote(kwargs['path'])
		easywebdav.Client.__init__(self, host, **kwargs)
		if ssl_version:
			self.session.adapters['https://'] = make_https_adapter(parse_ssl_version(ssl_version))()
		self.max_retry = max_retry
		self.retry_after = retry_after
		self.timeout = timeout
		self.url = url # for debug purposes

	def _send(self, *args, **kwargs):
		try:
			if self.max_retry is None:
				return easywebdav.Client._send(self, *args, **kwargs)
			else:
				clock = Clock(self.retry_after, timeout=self.timeout, max_count=self.max_count)
				while True:
					try:
						return easywebdav.Client._send(self, *args, **kwargs)
					except requests.exceptions.ConnectionError as e:
						info = e.args
						# extract information from (a certain type of) ConnectionErrors
						try:
							info = info[0]
						except IndexError:
							pass
						else:
							if isinstance(info, tuple):
								try:
									info = info[1]
								except IndexError:
									pass
						self.logger.warn("%s", info)
						debug_info = list(args)
						#debug_info.append(kwargs)
						#self.logger.debug(' %s %s %s %s', *debug_info)
						try:
							clock.wait(self.logger)
						except StopIteration:
							self.logger.error('too many connection attempts')
							break
				raise e
		except easywebdav.OperationFailed as e:
			path = args[1]
			if e.actual_code == 403:
				self.logger.error("access to '%s%s' forbidden", self.url, path)
			elif e.actual_code == 423: # 423 Locked
				self.logger.error("resource '%s%s' locked", self.url, path)
			raise e

	def _get_url(self, path):
		return easywebdav.Client._get_url(self, quote(path))

	def cd(self, path):
		easywebdav.Client.cd(self, quote(path))

	#def ls(self, remote_path):
	# We would like `ls` to return unquoted file paths, but files are listed as read-only named tuples
	# unfortunately. The :meth:`WebDAV._list` method should therefore unquote by itself.

	def upload(self, local_path_or_fileobj, remote_path):
		_easywebdav_adapter(self._upload, 'rb', local_path_or_fileobj, remote_path)

	def download(self, remote_path, local_path_or_fileobj):
		"""
		This code is partly borrowed from:
		https://github.com/amnong/easywebdav/blob/master/easywebdav/client.py

		Below follows the copyright notice of the easywebdav project which is supposed to be
		distributed under the ISC license:
		::

			Copyright (c) 2012 year, Amnon Grossman

			Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

			THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

		"""
		try:
			response = self._send('GET', remote_path, 200, stream=True)
		except easywebdav.OperationFailed as e:
			if e.actual_code == 404:
				self.logger.warning("the file is no longer available")
				self.logger.debug('%s', e)
		else:
			_easywebdav_adapter(self._download, 'wb', local_path_or_fileobj, response)

	def exists(self, remote_path):
		try:
			return easywebdav.Client.exists(self, remote_path)
		except easywebdav.OperationFailed as e:
			if e.actual_code == 423: # '423 Locked', therefore it exists!
				return True
			raise e



class WebDAV(Relay):
	"""
	Adds support for WebDAV remote hosts on top of :mod:`easywebdav`.

	Attributes:

		username (str): https username.

		password (str): https password.

		protocol (str): either 'http' or 'https'.

		certificate (str): path to a .pem certificate file.

		max_retry (bool or int): defines the maximum number of retries.
			Applies to connection failures.

		retry_after (int): defines interval time between retries in seconds.
			Applies to connection failures.

		ssl_version (int or str): any valid argument to :func:`~syncacre.base.ssl.parse_ssl_version`.

		verify_ssl (bool): if ``True``, check server's certificate.
	"""

	__protocol__ = ['webdav', 'https']

	def __init__(self, address, username=None, password=None, protocol=None, certificate=None, \
		max_retry=True, retry_after=None, logger=None, ssl_version=None, verify_ssl=True, **ignored):
		Relay.__init__(self, address, logger=logger)
		if PYTHON_VERSION == 3: # deal with encoding issues with requests
			username = username.encode('utf-8').decode('unicode-escape')
			password = password.encode('utf-8').decode('unicode-escape')
		self.username = username
		self.password = password
		self.protocol = protocol.lower()
		if self.protocol == 'webdav':
			self.protocol = 'https'
		self.certificate = certificate
		self.max_retry = max_retry
		self.retry_after = retry_after
		self.ssl_version = ssl_version
		self.verify_ssl = verify_ssl

	def open(self):
		kwargs = {}
		if self.certificate:
			kwargs['protocol'] = 'https'
			kwargs['cert'] = self.certificate
		if self.protocol:
			kwargs['protocol'] = self.protocol
		kwargs['verify_ssl'] = self.verify_ssl
		if self.ssl_version:
			kwargs['ssl_version'] = parse_ssl_version(self.ssl_version)
		try:
			self.address, self.path = self.address.split('/', 1)
			kwargs['path'] = self.path
		except ValueError:
			pass
		if self.max_retry is not True: # WebDAVClient has max_retry set; trust default value there
			kwargs['max_retry'] = self.max_retry
		if self.retry_after is not None:
			kwargs['retry_after'] = self.retry_after
		# url is for debug purposes
		try:
			url = '{}://{}/{}/'.format(self.protocol, self.address, self.path)
		except:
			try:
				url = '{}://{}/'.format(self.protocol, self.address)
			except:
				pass
		# establish connection (session)
		self.webdav = WebDAVClient(self.address, logger=self.logger, url=url, \
				username=self.username, password=self.password, \
				**kwargs)

	def diskFree(self):
		return None

	def hasPlaceholder(self, remote_file):
		return self.webdav.exists(self.placeholder(remote_file))

	def hasLock(self, remote_file):
		return self.webdav.exists(self.lock(remote_file))

	def _list(self, remote_dir, recursive=True, begin=None):
		if not remote_dir:
			remote_dir = '.' # easywebdav default
		try:
			ls = self.webdav.ls(remote_dir)
		except easywebdav.OperationFailed as e:
			if e.actual_code == 404:
				return []
			else:
				if e.actual_code != 403:
					self.logger.error("easywebdav.Client.ls('%s') failed", remote_dir)
				raise e
		if begin is None:
			if remote_dir[0] != '/':
				remote_dir = '/' + remote_dir
			if remote_dir[-1] != '/':
				remote_dir += '/'
			begin = len(remote_dir)
		# list names (not paths) of files (no directory)
		files = [ unquote(file.name[begin:]) for file in ls if file.contenttype ]
		if recursive:
			dirs = [ unquote(file.name) for file in ls \
				if file.contenttype ]
			files = list(itertools.chain(files, \
				*[ self._list(d, True, begin) for d in dirs \
					if len(remote_dir) < len(d.name) \
					and os.path.split(d.name[:-1])[1][0] != '.' ]))
		#print(('WebDAV._list: remote_dir, files', remote_dir, files))
		return files

	def _push(self, local_file, remote_file, makedirs=True):
		# webdav destination should be a path to file
		if makedirs:
			remote_dir, _ = os.path.split(remote_file)
			self.webdav.mkdirs(remote_dir)
		self.webdav.upload(local_file, remote_file)

	def _get(self, remote_file, local_file, makedirs=True):
		# local destination should be a file
		#print(('WebDAV._get: *args', remote_file, local_file, unlink))
		if makedirs:
			local_dir = os.path.dirname(local_file)
			if not os.path.isdir(local_dir):
				os.makedirs(local_dir)
		self.webdav.download(remote_file, local_file)

	def unlink(self, remote_file):
		#print('deleting {}'.format(remote_file)) # debug
		self.webdav.delete(remote_file)


