# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from syncacre.base.essential import *
from syncacre.base.ssl import *
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

	Tested with pure-ftpd, vsftpd and proftpd.

	Attributes:

		username (str): FTP username.

		password (str): FTP password.

		protocol (str): either 'ftp' or 'ftps' (case insensitive).

		encoding (str): encoding for file names.

		account (?): `acct` argument for :class:`ftplib.FTP` and :class:`ftplib.FTP_TLS`.

		certificate (str): path to .pem certificate file, or pair of paths (.cert.pem, .key.pem).

		certfile (str): path to .cert.pem certificate file.

		keyfile (str): path to .key.pem private key file; requires `certfile` to be defined.

		ssl_version (int or str): SSL version as supported by 
			:func:`~syncacre.base.ssl.parse_ssl_version`.

		verify_ssl (bool): if ``True`` check server's certificate; if ``None``
			check certificate if any; if ``False`` do not check certificate.
	
	"""

	__protocol__ = ['ftp', 'ftps']

	def __init__(self, address, username=None, password=None, protocol=None,
			encoding='utf-8', account=None, keyfile=None, certfile=None, context=None,
			certificate=None, verify_ssl=None, ssl_version=None,
			client='', logger=None, ui_controller=None, **ignored):
		IRelay.__init__(self, address, client=client, logger=logger,
				ui_controller=ui_controller)
		self.username = username
		self.password = password
		self.account = account # `acct` argument for FTP and FTP_TLS
		self.protocol = protocol.lower()
		self._encoding = encoding
		# certificate for FTP_TLS
		if certificate:
			self.certificate = certificate
		elif certfile:
			if keyfile: # a keyfile alone is useless
				self.certificate = (certfile, keyfile)
			else:
				self.certificate = certfile
		if keyfile and not certfile:
			self.logger.warning('`keyfile` requires `certfile` to be defined as well')
		# SSL arguments
		self.context = context # `context` argument for FTP_TLS
		if ssl_version:
			if context:
				self.logger.warning('`context` and `ssl_version` arguments are conflicting')
			ssl_version = parse_ssl_version(ssl_version)
			if isinstance(ssl_version, ssl.SSLContext):
				self.context = ssl_version
			else:
				self.context = ssl.SSLContext(ssl_version)
		if verify_ssl is None:
			if self.context is not None:
				self.context.verify_mode = ssl.CERT_OPTIONAL
		else:
			if self.context is None:
				self.context = ssl.SSLContext(ssl.PROTOCOL_TLS)
			if verify_ssl:
				self.context.verify_mode = ssl.CERT_REQUIRED
			else:
				self.context.verify_mode = ssl.CERT_NONE


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

	@property
	def certfile(self):
		if isinstance(self.certificate, tuple):
			return self.certificate[0]
		else:
			return self.certificate

	@property
	def keyfile(self):
		if isinstance(self.certificate, tuple):
			return self.certificate[1]
		else:
			return self.certificate

	
	def login(self):
		_user = self.username
		_pass = self.password
		if not _pass:
			if _user:
				_pass = self.ui_controller.requestCredential(self.address, _user)
			else:
				_user, _pass = self.ui_controller.requestCredential(self.address)
		while True:
			try:
				self.ftp.login(_user, _pass, self.account)
			except KeyboardInterrupt:
				raise
			except ssl.SSLError as e:
				self.logger.error("%s", e)
				if not self.ui_controller.getServerCertificate(self.ftp.sock):
					raise
				#continue # try again
			except IOError as e:
				import errno
				if e.errno == errno.EPIPE and self.protocol == 'ftp':
					self.logger.error("'%s' might exclusively accept SSL/TLS connections", self.address)
					return False
				else:
					raise
			except ftplib.error_perm as e:
				err_code = e.args[0][:3]
				if err_code == '530': # [vsftpd] 530 Login incorrect.
					print('wrong username or password; try again')
					_user, _pass = self.ui_controller.requestCredential(self.address)
					#continue # try again
				elif err_code == '500':
					# [pure-ftpd] 500 This security scheme is not implemented
					# [proftpd] 500 AUTH not understood
					self.logger.info(traceback.format_exc())
					self.logger.error("'%s' does not accept SSL/TLS connections", self.address)
					return False
				else:
					raise
			else:
				self.username = _user
				self.password = _pass
				return True # auth ok


	def open(self):
		self.ftp = None
		if self.protocol is None or self.protocol == 'ftps':
			self.ftp = ftplib.FTP_TLS(self.address,
					certfile=self.certfile, keyfile=self.keyfile, context=self.context)
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
		self._root = self.ftp.pwd()
		self._mlsd_support = True
		self._size_support = None # undefined
		self._size_needs_binary = None
		self._estimated_used = None
		self.repository_root = None


	def storageSpace(self):
		used = None
		if self.repository_root is not None and self._size_support is not False: # None is ok
			files = self._list(self.repository_root, recursive=True)
			if files:
				if self._size_needs_binary:
					self.ftp.voidcmd('TYPE I') # set binary mode
				f = 0
				if self._size_support is None:
					def no_support_msg(sure=False):
						if sure:
							w = 'does'
						else:
							w = 'may'
						return "server at '{}' {} not support 'SIZE' command".format(self.address, w)
					file = join(self._root, self.repository_root, files[f])
					while True: # should not iterate more than twice
						try:
							used = self.ftp.size(file)
						except ftplib.error_perm as e:
							err_code = e.args[0][:3]
							if err_code == '550':
								# [vsftpd] 550 Could not get file size.
								# [proftpd] 550 SIZE not allowed in ASCII mode
								if 'ASCII' in e.args[0].split(): # proftpd
									if not self._size_needs_binary:
										self._size_needs_binary = True
										self.ftp.voidcmd('TYPE I')
										continue # try again
								else:
									self.logger.critical("internal error: file '%s' does not exist", file)
							elif err_code == '500':
								# TODO: find a server without SIZE support and check error code
								self.logger.info(no_support_msg(True))
								break # do not raise the exception again
							else:
								self.logger.info(no_support_msg())
							raise
						break
					self._size_support = used is not None
					f += 1
				if self._size_support:
					if used is None:
						used = 0
					for file in files[f:]:
						s = self.ftp.size(join(self._root, self.repository_root, file))
						if s is None:
							raise RuntimeError("'SIZE {}' returned None".format(file))
						used += s
					used = float(used) / 1048576 # in MB
			else:
				used = 0
		return (used, None)


	def _list(self, remote_dir, recursive=True, append=''):
		if append:
			def _join(f): return join(append, f)
		else:
			def _join(f): return f
		remote_dir = asstr(remote_dir)
		if self.repository_root is None:
			self.repository_root = remote_dir
		fullpath = join(self._root, remote_dir)
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
					# initialize LIST related variables
					self._filename_in_list = 8
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
			for line in ls:
				parts = line.split(None, self._filename_in_list + 1)
				try:
					filename = parts[self._filename_in_list]
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
		fullpath = os.path.join(self._root, dirname)
		try:
			self.ftp.cwd(fullpath)
		except ftplib.error_perm as e:
			err_code = e.args[0][:3]
			if err_code == '550':
				# [pure-ftpd] 550 Can't change directory to ...: No such file or directory
				self.ftp.cwd(self._root)
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
		self.ftp.retrbinary('RETR ' + join(self._root, remote_file),
			open(local_file, 'wb').write)


	def unlink(self, remote_file):
		self.ftp.delete(join(self._root, remote_file))


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

