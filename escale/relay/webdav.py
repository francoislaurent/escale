# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent

# Copyright © 2017, François Laurent
#   new certificate verification feature
#   WebDAV.__send

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.exceptions import *
from escale.base.essential import *
from escale.base.timer import *
from escale.base.ssl import *
from escale.log import log_root
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
import traceback


## trying SO_REUSEADDR fix - doesn't work
#import socket
#try:
#	from urllib3.connection import HTTPConnection
#except ImportError:
#	pass
#else:
#	# modify globally :/
#	HTTPConnection.default_socket_options + [(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)]


# the following fix has been suggested in
# http://www.rfk.id.au/blog/entry/preparing-pyenchant-for-python-3/
if PYTHON_VERSION == 3:
	basestring = (str, bytes)
else:
	basestring = basestring


timeout_error_codes = [504]


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
	"""
	This code - especially the :meth:`download` method and the 
	:func:`_easywebdav_adapter` function - is partly borrowed from:
	https://github.com/amnong/easywebdav/blob/master/easywebdav/client.py

	Below follows the copyright notice of the easywebdav project which is
	distributed under the ISC license:
	::
		Copyright (c) 2011, Kenneth Reitz

		Copyright (c) 2012 year, Amnon Grossman

		Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

		THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
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
			self.session.mount('https://', make_https_adapter(parse_ssl_version(ssl_version))())
		self.max_retry = max_retry
		self.retry_after = retry_after
		self.timeout = timeout
		self.url = url # for debug purposes
		self._response = None

	def __send(self, method, path, expected_code, **kwargs): # originally easywebdav.Client._send
		# borrowed from original easywebdav code distributed under ISC license. See above
		url = self._get_url(path)
		response = self.session.request(method, url, allow_redirects=False, **kwargs)
		status_code = response.status_code
		if isinstance(expected_code, easywebdav.Number) and status_code != expected_code \
				or not isinstance(expected_code, easywebdav.Number) and status_code not in expected_code:
			response.close() # fix for SSLError [Errno 24] Too many open files
			raise easywebdav.OperationFailed(method, path, expected_code, status_code)
		return response

	def _send(self, *args, **kwargs):
		if self._response is not None:
			# not sure easywebdav fully consumes every response
			# see also http://docs.python-requests.org/en/master/user/advanced/#body-content-workflow
			self._response.close()
		try:
			if self.max_retry is None:
				self._response = self.__send(*args, **kwargs)
			else:
				clock = Clock(self.retry_after, timeout=self.timeout, max_count=self.max_retry)
				while True:
					try:
						self._response = self.__send(*args, **kwargs)
					except easywebdav.OperationFailed as e:
						_last_error = e
						if e.actual_code in timeout_error_codes:
							self.logger.debug("%s", e)
						else:
							raise
					else:
						break
					# wait
					try:
						clock.wait(self.logger)
						self.logger.debug('retrying')
					except StopIteration:
						self.logger.error('too many connection attempts')
						raise _last_error
		except requests.exceptions.SSLError as e:
			try:
				errno = e.args[0].args[0].args[0]
			except:
				pass
			else:
				if errno == 24:
					# SSLError: [Errno 24] Too many open files
					raise UnrecoverableError(e.args[0])
			raise e
		except easywebdav.OperationFailed as e:
			# log timeout errors (if not already done)
			if self.max_retry is None:
				if e.actual_code in timeout_error_codes:
					self.logger.debug("%s", e)
					raise
			# log 403 and 423 errors
			try:
				path = e.args[1]
			except:
				pass
			else:
				if e.actual_code == 403:
					self.logger.error("access to '%s%s' forbidden", self.url, path)
				elif e.actual_code == 423: # 423 Locked
					self.logger.debug("resource '%s%s' locked", self.url, path)
			raise e
		return self._response


	def _get_url(self, path):
		return easywebdav.Client._get_url(self, quote(asstr(path)))

	def cd(self, path):
		easywebdav.Client.cd(self, quote(asstr(path)))

	def ls(self, remote_path, recursive=False):
		if recursive:
			headers = {'Depth': 'infinity'}
		else:
			headers = {'Depth': '1'}
		response = self._send('PROPFIND', remote_path, (207, 301), headers=headers)

		# Redirect
		if response.status_code == 301:
			url = easywebdav.client.urlparse(response.headers['location'])
			return self.ls(url.path, recursive)

		tree = easywebdav.xml.fromstring(response.content)
		response.close()
		return [easywebdav.client.elem2file(elem) for elem in tree.findall('{DAV:}response')]

	def upload(self, local_path, remote_path):
		with open(local_path, 'rb') as f:
			self._upload(f, remote_path)

	def download(self, remote_path, local_path):
		try:
			response = self._send('GET', remote_path, 200, stream=True)
		except easywebdav.OperationFailed as e:
			if e.actual_code == 404:
				self.logger.warning("the file is no longer available")
				#self.logger.debug(traceback.format_exc()) # traceback will be logged by manager
			raise
		else:
			with open(local_path, 'wb') as f:
				self._download(f, response)
			response.close()

	def exists(self, remote_file):
		try:
			b = easywebdav.Client.exists(self, remote_file)
			return b
		except easywebdav.OperationFailed as e:
			if e.actual_code == 423: # '423 Locked', therefore it exists
				return True
			else:
				raise



class WebDAV(Relay):
	"""
	Adds support for WebDAV remote hosts on top of :mod:`easywebdav`.

	Attributes:

		username (str): https username.

		password (str): https password.

		protocol (str): either 'http' or 'https'.

		certificate (str): path to .pem certificate file, or pair of paths (.cert.pem, .key.pem).

		certfile (str): path to .cert.pem certificate file.

		keyfile (str): path to .key.pem private key file; requires `certfile` to be defined.

		ssl_version (int or str): any valid argument to 
			:func:`~escale.base.ssl.parse_ssl_version`.

		verify_ssl (bool): if ``False`` do not check server's certificate.

		max_retry (bool or int): defines the maximum number of retries.
			Applies to connection failures.

		retry_after (int): defines interval time between retries in seconds.
			Applies to connection failures.

	"""

	__protocol__ = ['webdav', 'https']

	def __init__(self, client, address, repository, username=None, password=None,
		protocol=None, certificate=None, certfile=None, keyfile=None, \
		ssl_version=None, verify_ssl=None, max_retry=None, retry_after=None, \
		config={}, **super_args):
		Relay.__init__(self, client, address, repository, **super_args)
		if PYTHON_VERSION == 3: # deal with encoding issues with requests
			username = username.encode('utf-8').decode('unicode-escape')
			password = password.encode('utf-8').decode('unicode-escape')
		self.username = username
		self.password = password
		self.protocol = protocol.lower()
		if self.protocol == 'webdav':
			self.protocol = 'https'
		# borrowing certificate/certfile/keyfile support from syncacre.relay.ftp
		self.certificate = certificate
		if certfile:
			if keyfile: # a keyfile alone is useless
				self.certificate = (certfile, keyfile)
			else:
				self.certificate = certfile
		if keyfile and not certfile:
			self.logger.warning('`keyfile` requires `certfile` to be defined as well')
		#
		if max_retry is None:
			max_retry = config.get('max retries', None)
		self.max_retry = max_retry
		self.retry_after = retry_after
		self.ssl_version = ssl_version
		self.verify_ssl = verify_ssl
		self._used_space = None
		self._infinity_depth = None

	def open(self):
		kwargs = {}
		if self.certificate:
			kwargs['protocol'] = 'https'
			kwargs['cert'] = self.certificate
		if self.protocol:
			kwargs['protocol'] = self.protocol
		if self.verify_ssl is not None:
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
		# request credential
		if not self.password:
			if self.username:
				self.password = self.ui_controller.requestCredential( \
						hostname=self.address, username=self.username)
			else:
				self.username, self.password = \
						self.ui_controller.requestCredential(hostname=self.address)
		# establish connection (session)
		self.webdav = WebDAVClient(self.address, logger=self.logger, url=url, \
				username=self.username, password=self.password, \
				**kwargs)

	def storageSpace(self):
		if isinstance(self._used_space, int): # in B
			self._used_space = float(self._used_space) / 1048576 # in MB
		return (self._used_space, None)

	def exists(self, remote_file, dirname=None):
		if dirname:
			#self.webdav.cd(join(self.repository, dirname))
			remote_file = join(self.repository, dirname, remote_file)
		else:
			remote_file = join(self.repository, remote_file)
		return self.webdav.exists(remote_file)

	def ls(self, remote_dir, recursive=False):
		#if hasattr(self, '_last_ls') and self._last_ls is not None:
		#	ls = self._last_ls
		#	self._last_ls = None
		#	return ls
		if recursive and self._infinity_depth is False:
			# infinite depth not allowed by WebDAV server
			ls = self.webdav.ls(remote_dir, False)
			remote_dir = os.path.join('/', remote_dir)
			ls = itertools.chain(ls,
					*[self.ls(unquote(entry.name), True) for entry in ls
						if not entry.contenttype \
						and os.path.relpath(entry.name, remote_dir) != '.' ])
			return ls
		first_recursive_call = recursive and \
				self._infinity_depth is None and \
				remote_dir == self.repository
		try:
			ls = self.webdav.ls(remote_dir, recursive)
		except easywebdav.OperationFailed as e:
			if e.actual_code != 404:
				if e.actual_code == 403:
					if first_recursive_call:
						# infinite depth may not be allowed by WebDAV server
						self._infinity_depth = False
						return self.ls(remote_dir, recursive)
					raise
				else:
					self.logger.warning("easywebdav.Client.ls('%s') failed", remote_dir)
					if e.actual_code not in timeout_error_codes:
						self.logger.debug(traceback.format_exc())
			return []
		else:
			if first_recursive_call:
				self._infinity_depth = True
			#self._last_ls = ls
			return ls

	def _list(self, remote_dir='', recursive=True, stats=[], storage_space=False):
		if remote_dir:
			relay_dir = join(self.repository, remote_dir)
		else:
			relay_dir = self.repository
		ls = self.ls(relay_dir, recursive)
		# list names (not paths) of files (no directory)
		files = [ (os.path.relpath(unquote(file.name[1:]), self.repository), file.size, file.mtime)
				for file in ls if file.contenttype ]
		if files:
			files, sizes, mtimes = zip(*files)
			if 'mtime' in stats:
				mtimes = [ time.strptime(t[5:], '%d %b %Y %H:%M:%S GMT') for t in mtimes ]
				files = list(zip(files, mtimes))
		#print(('WebDAV._list: remote_dir, files', remote_dir, files))
		return files

	def _push(self, local_file, remote_file, makedirs=True):
		# webdav destination should be a path to file
		remote_file = join(self.repository, remote_file)
		if makedirs:
			remote_dir, _ = os.path.split(remote_file)
			self.webdav.mkdirs(remote_dir)
		self.webdav.upload(local_file, remote_file)

	def _get(self, remote_file, local_file, makedirs=True):
		# local destination should be a file
		#print(('WebDAV._get: *args', remote_file, local_file, unlink))
		remote_file = join(self.repository, remote_file)
		if makedirs:
			local_dir = os.path.dirname(local_file)
			if not os.path.isdir(local_dir):
				os.makedirs(local_dir)
		self.webdav.download(remote_file, local_file)

	def unlink(self, remote_file):
		#print('deleting {}'.format(remote_file)) # debug
		remote_file = join(self.repository, remote_file)
		self.webdav.delete(remote_file)

	def purge(self, remote_dir=''):
		remote_dir = join(self.repository, remote_dir)
		self.webdav.rmdir(remote_dir, remote_dir, safe=False)

