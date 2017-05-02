# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from syncacre.base.essential import *
from syncacre.cli.auth import *
from .relay import IRelay
import ftplib
import ssl
import os
import itertools
import traceback



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
	
	"""

	__protocol__ = ['ftp', 'ftps']

	def __init__(self, address, username=None, password=None, protocol=None,
			encoding='utf-8', account=None, keyfile=None, context=None,
			certificate=None, verify_ssl=True, ssl_version=None,
			client='', logger=None, ui_controller=None, **ignored):
		IRelay.__init__(self, address, client=client, logger=logger,
				ui_controller=ui_controller)
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
			self.logger.warning("'verify_ssl' is not supported yet")


	@property
	def encoding(self):
		try:
			return self.ftp.encoding
		except AttributeError: # `ftp` not initialized or no `encoding` attribute
			return self._encoding
		

	@encoding.setter
	def encoding(self, enc):
		self._encoding = enc
		try:
			self.ftp.encoding = enc
		except AttributeError:
			pass

	
	def login(self):
		_user = self.username
		_pass = self.password
		if not _pass:
			if _user:
				_pass = self.ui_controller.requestCredential(self.address, _user)
			else:
				_user, _pass = self.ui_controller.requestCredential(self.address)
		first_iteration = True
		auth = True
		while auth:
			try:
				self.ftp.login(_user, _pass, self.account)
			except KeyboardInterrupt:
				raise
			except IOError as e:
				import errno
				if e.errno == errno.EPIPE and self.protocol == 'ftp':
					self.logger.error("'%s' may not accept non-SSL connections", self.address)
				return False
			except ftplib.error_perm as e:
				err_code = e.args[0][:3]
				if err_code == '530': # [vsftpd] 530 Login incorrect.
					if first_iteration:
						self.logger.info('missing or incorrect username and password')
					else:
						print('wrong username or password; try again')
					_user, _pass = self.ui_controller.requestCredential(self.address)
				elif err_code == '500': # [pure-ftpd] 500 This security scheme is not implemented
					assert first_iteration
					self.logger.error("'%s' does not accept SSL connections", self.address)
					return False
				else:
					raise
			else:
				auth = False
				self.username = _user
				self.password = _pass
			first_iteration = False
		return True


	def open(self):
		self.ftp = None
		if self.protocol is None or self.protocol == 'ftps':
			self.ftp = ftplib.FTP_TLS(self.address,
					keyfile=self.keyfile, certfile=self.certificate, context=self.context)
			if self.login():
				self.ftp.prot_p()
			else:
				if self.protocol == 'ftps': # TLS was explicit required
					notls_msg = "cannot connect to '{}' with TLS enabled".format(self.address)
					raise RuntimeError(notls_msg)
				self.ftp = None # try with SSL disabled
		if self.ftp is None:
			self.ftp = ftplib.FTP(self.address)
			if not self.login():
				if self.protocol == 'ftp':
					#self.logger.info("'protocol' should be 'ftps' instead of 'ftp'")
					self.logger.info("trying with setting: 'protocol = ftps'")
					self.protocol = 'ftps'
					return self.open()
				else:
					# ftps was tried before, therefore neither ftp nor ftps work
					raise RuntimeError('connection failed both with SSL enabled and SSL disabled')
		if 'UTF8' not in self.ftp.sendcmd('FEAT'):
			self.logger.debug('FTP server does not support unicode')
		self.ftp.encoding = self._encoding
		self.root = self.ftp.pwd()
		self._mlsd_support = True



	def _list(self, remote_dir, recursive=True, append=''):
		if append:
			def _join(f): return join(append, f)
		else:
			def _join(f): return f
		fullpath = join(self.root, remote_dir)
		files, dirs = [], []
		if self._mlsd_support:
			try:
				if PYTHON_VERSION == 3:
					ls = self.ftp.mlsd(fullpath)
					for f, info in ls:
						if info['type'] == 'dir':
							dirs.append(f)
						elif info['type'] == 'file':
							files.append(_join(f))
				elif PYTHON_VERSION == 2:
					ls = []
					self.ftp.retrlines('MLSD ' + fullpath, ls.append)
					for rep in ls:
						info, f = rep.split(None, 1)
						if 'ype=file' in info:
							files.append(_join(f))
						elif 'ype=dir' in info:
							dirs.append(f)
			except ftplib.error_perm as e:
				err_code = e.args[0][:3]
				if err_code == '500': # [vsftpd] 500 Unknown command.
					self._mlsd_support = False
				else:
					raise
		if not self._mlsd_support:
			try:
				self.ftp.cwd(fullpath)
			except ftplib.error_perm as e:
				err_code = e.args[0][:3]
				if err_code == '550': # [vsftpd] 550 Failed to change directory.
					return []
				else:
					raise
			ls = []
			try:
				self.ftp.retrlines('LIST -a', ls.append)
			except ftplib.error_perm as e:
				err_code = e.args[0][:3]
				if err_code == '522': # [vsftpd] 522 SSL connection failed: session reuse required
					self.logger.error("%s", e.args[0])
					self.logger.info("if the running FTP server is vsftpd, \n\tthis error can be fixed adding the line 'require_ssl_reuse=NO' to '/etc/vsftpd.conf'")
					raise
				else:
					raise
			for line in ls:
				try:
					filename = line.split(None, 9)[8]
				except IndexError:
					self.logger.debug("'LIST' returned '%s'", line)
					pass
				else:
					if line[0] == 'd':
						dirs.append(filename)
					elif line[0] == '-':
						files.append(_join(filename))
		if recursive and dirs:
			if dirs[0] == '.':
				dirs = dirs[2:]
			# recurrent call on directories
			files = list(itertools.chain(files,
				*[ self._list(join(remote_dir, d), True, append=_join(d))
					for d in dirs ]))
		return files


	def _push(self, local_file, remote_dest, makedirs=True):
		dirname, basename = os.path.split(remote_dest)
		fullpath = os.path.join(self.root, dirname)
		try:
			self.ftp.cwd(fullpath)
		except ftplib.error_perm as e:
			err_code = e.args[0][:3]
			if err_code == '550':
				# [pure-ftpd] 550 Can't change directory to ...: No such file or directory
				self.ftp.cwd(self.root)
				parts = os.path.normpath(dirname).split('/')
				for part in parts:
					if part:
						try:
							self.ftp.cwd(part)
						except ftplib.error_perm:
							self.ftp.mkd(part)
							self.ftp.cwd(part)
			else:
				raise
		self.ftp.storbinary('STOR ' + basename, open(local_file, 'rb'))


	def _get(self, remote_file, local_file, makedirs=True):
		if makedirs:
			local_dir = os.path.dirname(local_file)
			if not os.path.isdir(local_dir):
				os.makedirs(local_dir)
		self.ftp.retrbinary('RETR ' + join(self.root, remote_file),
			open(local_file, 'wb').write)


	def unlink(self, remote_file):
		self.ftp.delete(join(self.root, remote_file))


	def close(self):
		try:
			self.ftp.quit()
		except KeyboardInterrupt:
			# an interrupt may happen anytime
			self.ftp.close()
			raise
		except IOError as e:
			import errno
			if e.errno == errno.EPIPE:
				# [vsftpd] [Errno 32] Broken pipe
				pass
			else:
				# TODO: identify which errors are raised
				self.logger.debug(traceback.format_exc())
			self.ftp.close()
		except:
			# TODO: identify which errors are raised
			self.logger.debug(traceback.format_exc())
			self.ftp.close()

