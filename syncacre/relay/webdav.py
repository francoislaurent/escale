
from syncacre.base.essential import *
from syncacre.base.ssl import *
import ssl
from syncacre.log import log_root
from .relay import Relay

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

	Below follows the copyright notice of the easywebdav project:
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


class WebDAVClient(easywebdav.Client):#Object, 
	"""
	This class inheritates from and overloads some methods of :class:`easywebdav.client.Client`.
	"""
	def __init__(self, host, max_retry=360, retry_after=10, url='', logger=None, \
		**kwargs):
		if logger is None:
			logger = logging.getLogger(log_root).getChild('WebDAVClient')
		self.logger = logger
		easywebdav.Client.__init__(self, host, **kwargs)
		# temporary dirty fix for issue #14
		self.session.adapters['https://'] = make_https_adapter(ssl.PROTOCOL_SSLv23)()
		self.max_retry = max_retry
		self.retry_after = retry_after
		self.url = url # for debug purposes

	def _send(self, *args, **kwargs):
		try:
			if self.max_retry is None:
				return easywebdav.Client._send(self, *args, **kwargs)
			else:
				count = 0
				while count <= self.max_retry:
					try:
						easywebdav.Client._send(self, *args, **kwargs)
					except requests.exceptions.ConnectionError as e:
						info = e.args
						try:
							info = info[0]
						except IndexError:
							self.logger.warn("%s", info)
							return False
						else:
							if isinstance(info, tuple):
								try:
									info = info[1]
								except IndexError: #??
									pass
						count += 1
						if count <= self.max_retry:
							self.logger.warn("%s", info)
							debug_info = list(args)
							debug_info.append(kwargs)
							self.logger.debug(' %s %s %s %s', *debug_info)
							time.sleep(self.retry_after)
						else:
							return
				self.logger.error('too many connection attempts.')
				raise e
		except easywebdav.OperationFailed as e:
			if e.actual_code == 403:
				path = args[1]
				self.logger.error("access to '%s%s' forbidden", self.url, path)
			raise e

	def upload(self, local_path_or_fileobj, remote_path):
		_easywebdav_adapter(self._upload, 'rb', local_path_or_fileobj, remote_path)

	def download(self, remote_path, local_path_or_fileobj):
		response = self._send('GET', remote_path, 200, stream=True)
		_easywebdav_adapter(self._download, 'wb', local_path_or_fileobj, response)



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
	"""

	__protocol__ = ['webdav', 'https']

	def __init__(self, address, username=None, password=None, protocol=None, certificate=None, \
		max_retry=True, retry_after=None, logger=None, **ignored):
		Relay.__init__(self, address, logger=logger)
		if PYTHON_VERSION == 3: # deal with encoding issues with requests
			username = username.encode('utf-8').decode('unicode-escape')
			password = password.encode('utf-8').decode('unicode-escape')
		self.username = username
		self.password = password
		self.protocol = protocol
		self.certificate = certificate
		self.max_retry = max_retry
		self.retry_after = retry_after

	def open(self):
		kwargs = {}
		if self.certificate:
			kwargs['protocol'] = 'https'
			kwargs['cert'] = self.certificate
		if self.protocol:
			kwargs['protocol'] = self.protocol
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
		#self.webdav.session.headers['Charset'] = 'utf-8' # for Python 3

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
		files = [ file.name[begin:] for file in ls if file.contenttype ] # list names (not paths) of files (no directory)
		if recursive:
			files = list(itertools.chain(files, \
				*[ self._list(file.name, True, begin) for file in ls \
					if not file.contenttype \
						and len(remote_dir) < len(file.name) \
						and os.path.split(file.name[:-1])[1][0] != '.' ]))
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
		local_dir = os.path.dirname(local_file)
		if makedirs and not os.path.isdir(local_dir):
			os.makedirs(local_dir)
		self.webdav.download(remote_file, local_file)

	def unlink(self, remote_file):
		#print('deleting {}'.format(remote_file)) # debug
		self.webdav.delete(remote_file)


