# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from syncacre.base.essential import *
from .relay import IRelay
import ftplib
import os
import itertools



class FTP(IRelay):
	"""
	Adds support for FTP remote hosts on top of the :mod:`ftplib` standard library.

	Attributes:

		username (str): FTP username.

		password (str): FTP password.

		protocol (str): either 'ftp' or 'ftps' or 'ftp tls'.
	
	.. warning:: very experimental! Especially, SSL/TLS features ('ftps' and 'ftp tls') have not been tested.

	"""

	__protocol__ = ['ftp', 'ftps', 'ftp_tls', 'ftp tls']

	def __init__(self, address, username=None, password=None, protocol=None, logger=None, **ignored):
		IRelay.__init__(self, address, logger=logger)
		self.username = username
		self.password = password
		self.protocol = protocol.lower()

	def open(self):
		self.ftp = None
		if self.protocol is None or any([ self.protocol == p for p in ['ftp', 'ftps', 'ftp_tls'] ]):
			try:
				self.ftp = ftplib.FTP_TLS(self.address, self.username, self.password)
			except (ftplib.error_proto, ftplib.error_perm) as e:
				# TLS connection not supported?
				self.ftp = None
				if not (self.protocol is None or self.protocol == 'ftp'): # TLS was explicit required
					self.logger.warning("cannot connect to '%s' with TLS support", address)
					self.logger.debug(e)
					raise e
			except Exception as e:
				self.logger.debug(e)
				raise e
			else:
				print('TLS is ok?')
				self.ftp.prot_p()
		if self.ftp is None:
			try:
				self.ftp = ftplib.FTP(self.address, self.username, self.password)
			except Exception as e:
				self.logger.debug(e)
				raise e
		self.root = self.ftp.pwd()


	def _list(self, remote_dir, recursive=True, append=''):
		if append:
			def join(f): return os.path.join(append, f)
		else:
			def join(f): return f
		fullpath = os.path.join(self.root, remote_dir)
		files, dirs = [], []
		if PYTHON_VERSION == 3:
			ls = self.ftp.mlsd(fullpath)
			for f, info in ls:
				if info['type'] == 'dir':
					dirs.append(f)
				elif info['type'] == 'file':
					files.append(join(f))
		elif PYTHON_VERSION == 2:
			ls = []
			self.ftp.retrlines('MLSD ' + fullpath, ls.append)
			for rep in ls:
				info, f = rep.split(None, 1)
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
		dirname, basename = os.path.split(remote_dest)
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
		self.ftp.retrbinary('RETR ' + os.path.join(self.root, remote_file),
			open(local_file, 'wb').write)

	def unlink(self, remote_file):
		self.ftp.delete(os.path.join(self.root, remote_file))

	def close(self):
		try:
			self.ftp.quit()
		except Exception as e:
			self.logger.debug(e)
			self.ftp.close()

