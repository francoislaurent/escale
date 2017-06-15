# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent
#   Contributions:
#     * `filetype` argument and attribute
#     * initial `filter` method (without `include` and `exclude` support)

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


import time
import calendar
import os
import sys
import traceback
import re
from escale.base import *
from escale.base.timer import *
from escale.base.config import storage_space_unit
from escale.encryption.encryption import Plain
from math import *


class Manager(Reporter):
	"""
	Makes the glue between the local file system and the :mod:`~escale.relay` and 
	:mod:`~escale.encryption` layers.

	This class manages the meta information, file modifications and sleep times.

	Attributes:

		repository (escale.manager.AccessController): local file access controller.

		address (str): remote host address.

		directory (str): path to the repository on the remote host.

		encryption (escale.encryption.Cipher): encryption layer.

		relay (escale.relay.AbstractRelay): communication layer.

		timestamp (bool or str): if ``True`` (recommended), manages file modification times. 
			If `str`, in addition determines the timestamp format as supported by 
			:func:`time.strftime`.

		filetype (list of str): list of file extensions.

		include (str): regular expression to include files by name.

		exclude (str): regular expression to exclude files by name.

		tq_controller (escale.manager.TimeQuotaController): time and quota controller.

		count (int): puller count.

		pop_args (dict): extra keyword arguments for 
			:meth:`~escale.relay.AbstractRelay.pop`.

	"""
	def __init__(self, relay, repository=None, address=None, directory=None, \
		encryption=Plain(None), timestamp=True, refresh=True, clientname=None, \
		filetype=[], include=None, exclude=None, tq_controller=None, count=None, \
		**relay_args):
		Reporter.__init__(self, **relay_args)
		self.repository = repository
		if directory:
			if directory[0] == '/':
				directory = directory[1:]
		else:
			directory = ''
		self.encryption = encryption
		if timestamp is True:
			timestamp = '%y%m%d_%H%M%S'
		self.timestamp = timestamp
		self.tq_controller = tq_controller
		if filetype:
			self.filetype = [ f if f[0] == '.' else '.' + f
					for f in filetype ]
		else:
			self.filetype = []
		self.include = None
		if include:
			try:
				self.include = re.compile(include)
			except:
				self.logger.error("wrong filename pattern '%s'", include)
				self.logger.debug(traceback.format_exc())
		self.exclude = None
		if exclude:
			try:
				self.exclude = re.compile(exclude)
			except:
				self.logger.error("wrong filename pattern '%s'", exclude)
				self.logger.debug(traceback.format_exc())
		self.pop_args = {}
		arg_map = [('locktimeout', 'lock_timeout')]
		for cfg_arg, rel_arg in arg_map:
			if cfg_arg in relay_args:
				relay_args[rel_arg] = relay_args.pop(cfg_arg)
		self.relay = relay(clientname, address, directory, **relay_args)
		if tq_controller is not None:
			self.tq_controller.quota_read_callback = self.relay.storageSpace
		if count:
			self.pop_args['placeholder'] = count


	# transitional alias properties
	@property
	def path(self):
		return self.repository.path
	@property
	def mode(self):
		return self.repository.mode
	@property
	def address(self):
		return self.relay.address
	@property
	def dir(self):
		return self.relay.directory

	@property
	def count(self):
		return self.pop_args.get('placeholder', None)


	def run(self):
		"""
		Runs the manager.

		Example:
		::

			from escale.manager import Manager
			from escale.relay   import WebDAV

			Manager(WebDAV,
				remote_host,
				path_to_local_repository,
				path_to_remote_repository
				).run()

		"""
		self.logger.debug("connecting to '%s'", self.relay.address)
		try:
			self.relay.open()
		except:
			self.logger.critical("failed to connect to '%s'", self.relay.address)
			self.logger.debug(traceback.format_exc())
			raise
		else:
			self.logger.debug('connected')
		# initial state
		_check_sanity = True
		_fresh_start = True
		_last_error_time = 0
		new = False
		while True:
			try:
				if _check_sanity:
					self.sanityCheck()
					_check_sanity = False
				if self.mode != 'upload':
					new |= self.download()
				if self.mode != 'download':
					new |= self.upload()
				if _fresh_start:
					if not new:
						self.logger.info('repository is up to date')
					_fresh_start = False
				if not self.tq_controller.wait():
					break
			except ExpressInterrupt as e:
				raise
			except Exception as e:
				t = time.time()
				if t - _last_error_time < 1: # the error repeats too fast; abort
					# last_error is defined
					if type(e) == type(last_error):
						break
				last_error = e
				_last_error_time = t
				self.logger.critical(traceback.format_exc())
				_check_sanity = True # check again for corrupted files
		# close and clear everything
		try:
			self.relay.close()
		except:
			self.logger.error("cannot close the connection to '%s'", self.relay.address)
			self.logger.debug(traceback.format_exc())
		try:
			raise last_error
		except UnboundLocalError:
			self.logger.info('exiting')


	def filter(self, files):
		"""
		Applies filters on a list of file paths.

		Arguments:

			files (list): list of file paths.

		Returns:

			list: list of selected file paths from ``files``.
		"""
		if self.filetype:
			files = [ f for f in files if os.path.splitext(f)[1] in self.filetype ]
		if self.include:
			files = [ f for f in files if self.include.match(os.path.basename(f)) ]
		if self.exclude:
			files = [ f for f in files if not self.exclude.match(os.path.basename(f)) ]
		return files

	def sanityCheck(self):
		"""
		Performs sanity checks and fixes the corrupted files.
		"""
		for lock in self.relay.listCorrupted():
			remote_file = lock.target
			local_file = self.repository.accessor(remote_file)
			self.logger.info("fixing uncompleted transfer: '%s'", remote_file)
			self.relay.repair(lock, local_file)

	def download(self):
		"""
		Finds out which files are to be downloaded and download them.
		"""
		remote = self.filter(self.relay.listReady())
		new = False
		for remote_file in remote:
			local_file = self.repository.writable(remote_file)
			if not local_file:
				# update not allowed
				continue
			last_modified = None
			if self.timestamp:
				meta = self.relay.getMetaInfo(remote_file)
				if meta:
					with open(meta, 'r') as f:
						# meta information is assumed to be ascii
						last_modified = f.readline().rstrip()
					os.unlink(meta)
					if last_modified:
						last_modified = time.strptime(last_modified, self.timestamp)
						last_modified = calendar.timegm(last_modified) # remote_mtime
					else:
						# if self.timestamp is defined, then meta information should as well
						self.logger.warning("corrupt meta information for file '%s'", remote_file)
			if os.path.isfile(local_file):
				if last_modified and last_modified <= floor(os.path.getmtime(local_file)):
					if self.count == 1:
						# no one else will ever download the current copy of the regular file
						# on the relay; delete it
						# this fixes the consequences of a bug introduced somewhere in the 0.4
						# family
						self.logger.info("deleting duplicate or outdated file '%s'", remote_file)
						self.relay.delete(remote_file)
					continue
				msg = "updating local file '%s'"
			else:
				msg = "downloading file '%s'"
			self.repository.confirmPull(local_file)
			new = True
			temp_file = self.encryption.prepare(local_file)
			self.logger.info(msg, remote_file)
			try:
				with self.tq_controller.pull(temp_file):
					ok = self.relay.pop(remote_file, temp_file, blocking=False, **self.pop_args)
			except RuntimeError: # TODO: define specific exceptions
				ok = False
			if ok:
				self.logger.debug("file '%s' successfully downloaded", remote_file)
			elif ok is not None:
				self.logger.error("failed to download '%s'", remote_file)
			self.encryption.decrypt(temp_file, local_file)
			if last_modified:
				os.utime(local_file, (time.time(), last_modified))
		return new

	def upload(self):
		"""
		Finds out which files are to be uploaded and upload them.
		"""
		local = self.localFiles()
		remote = self.relay.listTransfered('', end2end=False)
		new = False
		for local_file in local:
			remote_file = os.path.relpath(local_file, self.path) # relative path
			if PYTHON_VERSION == 2 and isinstance(remote_file, unicode) and \
				remote and isinstance(remote[0], str):
				remote_file = remote_file.encode('utf-8')
			modified = False # if no remote copy, this is ignored
			if self.timestamp: # check file last modification time
				local_mtime = floor(os.path.getmtime(local_file))
				last_modified = time.gmtime(local_mtime) # UTC
				last_modified = time.strftime(self.timestamp, last_modified)
				if remote_file in remote:
					meta = self.relay.getMetaInfo(remote_file)
					if meta:
						with open(meta, 'r') as f:
							remote_mtime = f.readline().rstrip()
						os.unlink(meta)
						if remote_mtime:
							remote_mtime = time.strptime(remote_mtime, self.timestamp)
							remote_mtime = calendar.timegm(remote_mtime)
							modified = remote_mtime < int(local_mtime)
						else: # no meta information
							modified = True
							# this may not be true, but this will update the meta
							# information with a valid content.
					#else: (TODO) directly read mtime on remote copy?
			else:
				last_modified = None
			if remote_file not in remote or modified:
				self.repository.confirmPush(local_file)
				new = True
				temp_file = self.encryption.encrypt(local_file)
				self.logger.info("uploading file '%s'", remote_file)
				try:
					with self.tq_controller.push(local_file):
						ok = self.relay.push(temp_file, remote_file,
							blocking=False, last_modified=last_modified)
				except QuotaExceeded as e:
					self.logger.info("%s; no more files can be sent", e)
					ok = False
				if ok:
					self.logger.debug("file '%s' successfully uploaded", remote_file)
				elif ok is not None:
					self.logger.warning("failed to upload '%s'", remote_file)
		return new

	def localFiles(self, path=None):
		"""
		Transitional method.

		Use ``self.repository.readableFiles`` instead.
		"""
		return self.repository.readable(self.filter(self.repository.listFiles(path)))

