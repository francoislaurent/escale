# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.exceptions import *
from escale.base.essential import *
from escale.base.timer import *
from ..relay import Relay
from .client import *

import os
import sys
import time
import traceback


timeout_error_codes = [504]


class WebDAV(Relay, Client):
	"""
	Backend for WebDAV servers.

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
			Applies to connection failures (deprecated).

		retry_after (int): defines interval time between retries in seconds.
			Applies to connection failures (deprecated).

	"""

	__protocol__ = ['webdav', 'http', 'https']

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
		# protocol
		protocol = protocol.lower()
		if protocol == 'webdav':
			protocol = 'https'
		elif protocol not in ['http', 'https']:
			raise ValueError('wrong protocol')
		# port
		try:
			port = super_args.pop('port')
		except KeyError:
			port = ''#{'http': '80', 'https': '443'}[protocol]
		if port:
			port = ':'+port
		# baseurl
		baseurl = ''.join((protocol, '://', address, port))
		if repository and repository != '/':
			if repository[0] != '/':
				repository = '/'+repository
			baseurl += repository
		# certificate
		# borrowing certificate/certfile/keyfile support from syncacre.relay.ftp
		if certfile:
			if keyfile: # a keyfile alone is useless
				certificate = (certfile, keyfile)
			else:
				certificate = certfile
		if keyfile and not certfile:
			self.logger.warning('`keyfile` requires `certfile` to be defined as well')
		# init webdav client
		Client.__init__(self, baseurl, username, password,
				certificate, verify_ssl, ssl_version)
		# not implemented
		if max_retry is None and 'max retries' in config:
			max_retry = int(config['max retries'])
		self.max_retry = max_retry
		self.retry_after = retry_after
		# 
		self._used_space = None

	def open(self):
		# request credential
		if not self.password:
			if self.username:
				self.password = self.ui_controller.requestCredential( \
						hostname=self.address, username=self.username)
			else:
				self.username, self.password = \
						self.ui_controller.requestCredential(hostname=self.address)
			self.auth = (self.username, self.password)

	def storageSpace(self):
		if isinstance(self._used_space, int): # in B
			self._used_space = float(self._used_space) / 1048576 # in MB
		return (self._used_space, None)

	def exists(self, remote_file, dirname=None):
		if dirname:
			remote_file = join(dirname, remote_file)
		return Client.exists(self, remote_file)

	def ls(self, remote_dir, recursive=False):
		try:
			return Client.ls(self, remote_dir, recursive)
		except UnexpectedResponse as e:
			if e.errno != 404:
				if e.errno in [403, 500]:
					raise
				else:
					self.logger.warning("Client.ls('%s') failed", remote_dir)
					if e.errno not in timeout_error_codes:
						self.logger.debug(traceback.format_exc())
			return []

	def _list(self, remote_dir='', recursive=True, stats=[], storage_space=False):
		ls = self.ls(remote_dir, recursive)
		# exclude directories
		files = [ (file.name, file.size, file.mtime)
				for file in ls if file.contenttype ]
		if files:
			files, sizes, mtimes = zip(*files)
			if not remote_dir or remote_dir == '/':
				self._used_space = sum(sizes)
			if stats:
				files = [ files ]
				for m in stats:
					if m == 'mtime':
						mtimes = [ time.strptime(t[5:], '%d %b %Y %H:%M:%S GMT') for t in mtimes ]
						files.append(mtimes)
					elif m == 'size':
						files.append(sizes)
				files = zip(*files)
		#print(('WebDAV._list: remote_dir, files', remote_dir, files))
		return files

	def _wait_on_error(self, func, *args, **kwargs):
		error_codes = kwargs.pop('error_codes', [423]+timeout_error_codes)
		clock = None
		while True:
			try:
				return func(*args, **kwargs)
			except UnexpectedResponse as e:
				if not isinstance(error_codes, (tuple, list)):
					error_codes = [ error_codes ]
				if e.errno in error_codes:
					# resource locked or gateway timeout
					self.logger.debug("%s", e)
					if clock is None:
						clock = Clock(initial_delay=2, max_delay=20, timeout=300)
					try:
						clock.wait(logger=self.logger)
					except StopIteration:
						self.logger.debug('timeout')
						raise
				else:
					raise
			else:
				break

	def _push(self, local_file, remote_file, makedirs=True):
		# webdav destination should be a path to file
		if makedirs:
			remote_dir = os.path.dirname(remote_file)
			self.mkdirs(remote_dir)
		self.upload(local_file, remote_file)

	def _get(self, remote_file, local_file, makedirs=True):
		# local destination should be a file
		#print(('WebDAV._get: *args', remote_file, local_file, unlink))
		if makedirs:
			local_dir = os.path.dirname(local_file)
			if not os.path.isdir(local_dir):
				os.makedirs(local_dir)
		self._wait_on_error(self.download, remote_file, local_file)

	def unlink(self, remote_file):
		#print('deleting {}'.format(remote_file)) # debug
		# `Relay.delete` and `Client.delete` conflict together
		self._wait_on_error(Client.delete, self, remote_file)

	def purge(self, remote_dir=''):
		self.rmdir(remote_dir)

	def acquireLock(self, remote_file, mode=None, blocking=True):
		while True:
			try:
				return Relay.acquireLock(self, remote_file, mode, blocking)
			except UnexpectedResponse as e:
				if blocking and e.actual_code == 423:
					continue
				raise
			break

