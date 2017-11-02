# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base import *
from escale.base.ssl import *
from escale.cli.auth import *
from .relay import Relay
import ftplib
import ssl
import os
import itertools
import traceback



if PYTHON_VERSION == 3:
	class _FTP_TLS(ftplib.FTP_TLS):
		"""Explicit FTPS, with shared TLS session.

		This code is borrowed from http://stackoverflow.com/questions/14659154/ftpes-session-reuse-required#26452738
		"""
		def ntransfercmd(self, cmd, rest=None):
			conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
			if self._prot_p:
				conn = self.context.wrap_socket(conn,
					server_hostname=self.host,
					session=self.sock.session) # this is the fix
			return conn, size
elif PYTHON_VERSION == 2:
	_FTP_TLS = ftplib.FTP_TLS



class FTP(Relay):
	"""
	Add support for FTP remote hosts on top of the :mod:`ftplib` standard library.

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
			:func:`~escale.base.ssl.parse_ssl_version`.

		verify_ssl (bool): if ``True`` check server's certificate; if ``None``
			check certificate if any; if ``False`` do not check certificate.
	
	"""

	__protocol__ = ['ftp', 'ftps']

	def __init__(self, client, address, repository, username=None, password=None,
			protocol=None, encoding='utf-8', account=None, keyfile=None, certfile=None,
			context=None, certificate=None, verify_ssl=None, ssl_version=None,
			**super_args):
		Relay.__init__(self, client, address, asstr(repository), **super_args)
		self.username = username
		self.password = password
		self.account = account # `acct` argument for FTP and FTP_TLS
		self.protocol = protocol.lower()
		self._encoding = encoding
		# certificate for FTP_TLS
		self.certificate = certificate
		if certfile:
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
		# note from https://docs.python.org/2/library/ssl.html#ssl-security :
		# > In client mode, CERT_OPTIONAL and CERT_REQUIRED are equivalent unless anonymous ciphers are enabled (they are disabled by default).
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
			except ExpressInterrupt:
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
				if err_code == '530':
					# [vsftpd] 530 Login incorrect.
					# [pure-ftpd] 530 Login authentication failed
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
			self.ftp = _FTP_TLS(self.address,
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
		if self._root:
			self.repository = os.path.join(self._root, self.repository)
		self._mlsd_support = False
		self._size_support = None # undefined
		self._size_needs_binary = None
		self._estimated_used = None

	def _request(self, callback, *args, **kwargs):
		"""
		Wrap method calls on object of type ftplib.FTP. Reconnect to server if connection has timed out.

		There is no need to wrap successive calls unless some significant amount of time can be spent
		between these calls. Wrap only the first call.
		"""
		try:
			response = callback(*args, **kwargs)
		except ftplib.error_temp as e:
			# handle only "421 No transfer timeout"
			err_code = e.args[0][:3]
			if err_code != '421':
				raise
			# connection unilaterally closed by server
			self.ftp.close()
			self.logger.debug("reconnecting to '%s'", self.address)
			if isinstance(self.ftp, _FTP_TLS):
				self.ftp = _FTP_TLS(self.address,
					certfile=self.certfile, keyfile=self.keyfile, context=self.context)
				self.ftp.login(self.username, self.password, self.account)
				self.ftp.prot_p()
			else:
				self.ftp = ftplib.FTP(self.address)
				self.ftp.login(self.username, self.password, self.account)
			self.ftp.encoding = self._encoding
			callback = getattr(self.ftp, callback.__name__)
			response = callback(*args, **kwargs)
		return response


	def size(self, remote_file, fail=False):
		remote_file = join(self.repository, remote_file)
		if self._size_needs_binary:
			self._request(self.ftp.voidcmd, 'TYPE I') # set binary mode
		if self._size_support is None:
			def no_support_msg(sure=False):
				if sure:
					w = 'does'
				else:
					w = 'may'
				return "server at '{}' {} not support 'SIZE' command".format(self.address, w)
			size = None
			while True: # should not iterate more than twice
				try:
					size = self._request(self.ftp.size, remote_file)
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
						elif fail:
							self.logger.critical("internal error: file '%s' does not exist",
								remote_file)
					elif err_code == '500':
						# TODO: find a server without SIZE support and check error code
						self.logger.info(no_support_msg(True))
						if fail:
							break # do not raise the exception again
					else:
						self.logger.info(no_support_msg())
					if fail:
						raise
				break
			self._size_support = size is not None
		else:
			try:
				size = self._request(self.ftp.size, remote_file)
			except ftplib.error_perm as e:
				#err_code = e.args[0][:3]
				#if err_code == '550':
				#	# [proftpd] No such file or directory
				if fail:
					raise
				else:
					size = None
		return size


	def storageSpace(self):
		used = None
		if self.repository is not None and self._size_support is not False: # None is ok
			files = self._list(recursive=True)
			if files:
				if self._size_needs_binary:
					self.ftp.voidcmd('TYPE I') # set binary mode
				f = 0
				if self._size_support is None:
					used = self.size(files[f], fail=True)
					if self._size_support:
						f += 1
				if self._size_support:
					if used is None:
						used = 0
					for file in files[f:]:
						s = self.ftp.size(join(self.repository, file))
						if s is None:
							raise RuntimeError("'SIZE {}' returned None".format(file))
						used += s
					used = float(used) / 1048576 # in MB
			else:
				used = 0
		return (used, None)


	def _list(self, remote_dir='', recursive=True, stats=[]):
		remote_dir = asstr(remote_dir)
		if remote_dir:
			def _join(f): return os.path.join(remote_dir, f)
			fullpath = os.path.join(self.repository, remote_dir)
		else:
			def _join(f): return f
			fullpath = self.repository
		files, dirs = [], []
		if self._mlsd_support:
			try:
				if PYTHON_VERSION == 3:
					ls = self._request(self.ftp.mlsd, fullpath)
					for f, info in ls:
						print(info) # has it ever been tested?
						if info['type'] == 'dir':
							dirs.append(f)
						elif info['type'] == 'file':
							file = _join(f)
							if 'mtime' in stats:
								mtime = time.strptime(info['modify'], '%Y%m%d%H%M%S')
								file = (file, mtime)
							files.append(file)
				elif PYTHON_VERSION == 2:
					ls = []
					self._request(self.ftp.retrlines, 'MLSD ' + fullpath, ls.append)
					for rep in ls:
						info, f = rep.split(None, 1)
						if 'ype=file' in info:
							file = _join(f)
							if 'mtime' in stats:
								if info.startswith('modify=') and info[21]==';':
									mtime = time.strptime(info[7:21], '%Y%m%d%H%M%S')
									file = (file, mtime)
							files.append(file)
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
			self._filename_in_list = 8
			try:
				self._request(self.ftp.cwd, fullpath)
			except ftplib.error_perm as e:
				err_code = e.args[0][:3]
				if err_code == '550': # [vsftpd] 550 Failed to change directory.
					return []
				else:
					raise
			ls = []
			try:
				self.ftp.retrlines('LIST -a', ls.append) # --full-time
			except ftplib.error_perm as e:
				err_code = e.args[0][:3]
				if err_code == '522': # [vsftpd] 522 SSL connection failed: session reuse required
					self.logger.error("%s", e.args[0])
					if PYTHON_VERSION == 2:
						self.logger.info("if the running FTP server is vsftpd, \n\tthis error can be fixed adding the line 'require_ssl_reuse=NO' to '/etc/vsftpd.conf'")
						self.logger.info(" another solution consists of switching to Python 3.6+")
					# the _FTP_TLS fix is supposed to solve this vsftpd issue
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
						file = _join(filename)
						if stats: # ['mtime']
							mtime = None
							#try:
							#	# with minute precision, timestamping is not reliable
							#	mtime = time.strptime(' '.join(line.split()[5:8]), '%b %d %H:%M')
							#except:
							#	pass
							file = (file, mtime)
						files.append(file)
		if recursive and dirs:
			if dirs[0] == '.':
				dirs = dirs[2:]
			# recurrent call on directories
			files = list(itertools.chain(files,
				*[ self._list(os.path.join(remote_dir, d), recursive=True, stats=stats)
					for d in dirs ]))
		return files


	def exists(self, remote_file, dirname=None):
		if self._size_support:
			if dirname:
				remote_file = join(dirname, remote_file)
			size = self.size(remote_file)
			# Py3 does not compare `int` and `None`
			return size is not None and 0 <= size
		else:
			return Relay.exists(self, remote_file, dirname=dirname)


	def _push(self, local_file, remote_dest, makedirs=True):
		dirname, basename = os.path.split(remote_dest)
		fullpath = os.path.join(self.repository, dirname)
		try:
			self._request(self.ftp.cwd, fullpath)
		except ftplib.error_perm as e:
			err_code = e.args[0][:3]
			if err_code == '550':
				# [pure-ftpd] 550 Can't change directory to ...: No such file or directory
				if self._root:
					self.ftp.cwd(self._root)
					dirname = os.path.relpath(fullpath, self._root)
				else:
					self.ftp.cwd('/')
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
		self._request(self.ftp.retrbinary, 'RETR ' + join(self.repository, remote_file),
				open(local_file, 'wb').write)


	def unlink(self, remote_file):
		self._request(self.ftp.delete, join(self.repository, remote_file))


	def purge(self, remote_dir=''):
		relay_dir = os.path.join(self.repository, asstr(remote_dir))
		ls = self._request(self.ftp.nslt, '-a', relay_dir)
		for _entry in ls:
			entry = os.path.join(relay_dir, _entry)
			try:
				self.ftp.delete(entry)
			except ftplib.all_errors:
				# TODO: find out which errors exactly
				self.purge(entry)
		self.ftp.rmd(relay_dir)


	def close(self):
		try:
			self.ftp.quit()
		except ExpressInterrupt:
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
		except ftplib.error_perm as e:
			err_code = e.args[0][:3]
			if err_code not in ['421']:
				# TODO: identify which other errors are raised
				self.logger.debug(traceback.format_exc())
			self.ftp.close()
		except:
			# TODO: identify which errors are raised
			self.logger.debug(traceback.format_exc())
			self.ftp.close()

