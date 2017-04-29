# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from syncacre.base.essential import *
from .relay import IRelay
import ftplib
import ssl
import os
import itertools



class FTP(IRelay):
	"""
	Adds support for FTP remote hosts on top of the :mod:`ftplib` standard library.

	Attributes:

		username (str): FTP username.

		password (str): FTP password.

		protocol (str): either 'ftp' or 'ftps' (case insensitive).

		encoding (str): encoding for file names.

		account (?): `acct` argument for :class:`ftplib.FTP` and :class:`ftplib.FTP_TLS`.

		keyfile (str): `keyfile` argument for :class:`ftplib.FTP_TLS`.

		certificate (str): path to a certificate file.

		ssl_version (int or str): SSL version as supported by 
			:func:`~syncacre.base.ssl.parse_ssl_version`.
	
	.. warning:: SSL/TLS features are experimental! They have not been tested yet.

	"""

	__protocol__ = ['ftp', 'ftps']

	def __init__(self, address, username=None, password=None, protocol=None,
			encoding='utf-8', account=None, keyfile=None, context=None,
			certificate=None, verify_ssl=True, ssl_version=None,
			client='', logger=None, **ignored):
		IRelay.__init__(self, address, client=client, logger=logger)
		self.username = username
		self.password = password
		self.protocol = protocol.lower()
		self._encoding = encoding
		self.account = account # `acct` argument for FTP and FTP_TLS
		self.keyfile = keyfile # `keyfile` argument for FTP_TLS
		self.context = context # `context` argument for FTP_TLS
		self.certificate = certificate # `certfile` argument for FTP_TLS
		if ssl_version: # compatibility argument ...
			ssl_version = parse_ssl_version(ssl_version)
			if isinstance(ssl_version, ssl.SSLContext):
				self.context = ssl_version
			else:
				self.context = ssl.SSLContext(ssl_version)
		if not verify_ssl:
			# TODO: `context` may be the place where to turn verification off
			logger.warning("'verify_ssl' is not supported yet")


	@property
	def encoding(self):
		try:
			return self.ftp.encoding
		except AttributeError: # `ftp` not initialized or no `encoding` attribute
			return self._encoding
		

	@encoding.setter
	def encoding(self, e):
		self._encoding = e
		try:
			self.ftp.encoding = e
		except AttributeError:
			pass


	def open(self):
		self.ftp = None
		if self.protocol is None or any([ self.protocol == p for p in ['ftps'] ]):
			try:
				self.ftp = ftplib.FTP_TLS(self.address,
						self.username, self.password, self.account,
						self.keyfile, self.certificate, self.context)
			except (ftplib.error_proto, ftplib.error_perm) as e:
				# TLS connection not supported?
				self.ftp = None
				if self.protocol == 'ftps': # TLS was explicit required
					self.logger.warning("cannot connect to '%s' with TLS support", address)
					self.logger.debug(e)
					raise e
			except Exception as e:
				self.logger.debug(e)
				raise e
			else:
				# never reached this point
				self.ftp.prot_p()
		if self.ftp is None:
			try:
				self.ftp = ftplib.FTP(self.address, self.username, self.password, self.account)
			except Exception as e:
				self.logger.debug(e)
				raise e
		if 'UTF8' not in self.ftp.sendcmd('FEAT'):
			logger.debug('FTP server does not support unicode')
		self.ftp.encoding = self._encoding
		self.root = self.ftp.pwd()



	def _list(self, remote_dir, recursive=True, append=''):
		if append:
			def join(f): return os.path.join(append, f)
		else:
			def join(f): return f
		fullpath = os.path.join(self.root, self._encode(remote_dir))
		files, dirs = [], []
		if PYTHON_VERSION == 3:
			ls = self.ftp.mlsd(fullpath)
			for f, info in ls:
				f = self._decode(f)
				if info['type'] == 'dir':
					dirs.append(f)
				elif info['type'] == 'file':
					files.append(join(f))
		elif PYTHON_VERSION == 2:
			ls = []
			self.ftp.retrlines('MLSD ' + fullpath, ls.append)
			for rep in ls:
				info, f = rep.split(None, 1)
				f = self._decode(f)
				if 'ype=file' in info:
					files.append(join(f))
				elif 'ype=dir' in info:
					dirs.append(f)
		if recursive and dirs:
			if dirs[0] == '.':
				dirs = dirs[2:]
			# recurrent call on directories
			files = list(itertools.chain(files,
				*[ self._list(os.path.join(remote_dir, d), True, append=join(d))
					for d in dirs ]))
		return files


	def _push(self, local_file, remote_dest, makedirs=True):
		dirname, basename = os.path.split(self._encode(remote_dest))
		try:
			self.ftp.cwd(os.path.join(self.root, dirname))
		except ftplib.error_perm as e:
			# TODO: check that error message is
			# "550 Can't change directory to ...: No such file or directory"
			self.ftp.cwd(self.root)
			parts = os.path.normpath(dirname).split('/')
			for part in parts:
				if part:
					try:
						self.ftp.cwd(part)
					except ftplib.error_perm as e:
						self.ftp.mkd(part)
						self.ftp.cwd(part)
		self.ftp.storbinary('STOR ' + basename, open(local_file, 'rb'))


	def _get(self, remote_file, local_file, makedirs=True):
		if makedirs:
			local_dir = os.path.dirname(local_file)
			if not os.path.isdir(local_dir):
				os.makedirs(local_dir)
		self.ftp.retrbinary('RETR ' + os.path.join(self.root, self._encode(remote_file)),
			open(local_file, 'wb').write)


	def unlink(self, remote_file):
		self.ftp.delete(os.path.join(self.root, self._encode(remote_file)))


	def close(self):
		try:
			self.ftp.quit()
		except Exception as e:
			self.logger.debug(e)
			self.ftp.close()


	def _encode(self, filename):
		return filename


	def _decode(self, filename):
		return filename


