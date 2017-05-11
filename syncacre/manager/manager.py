# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

# Copyright (c) 2017, Institut Pasteur
#   Contributor: François Laurent
#   Contributions:
#     * `filetype` argument and attribute
#     * initial `filter` method (without `pattern` support)
#     * `UnrecoverableError` handling

import time
import calendar
import os
import sys
import traceback
import re
from syncacre.base import (PYTHON_VERSION,
	UnrecoverableError,
	join,
	Clock,
	Reporter,
	storage_space_unit)
from syncacre.encryption import Plain
from math import *


class Manager(Reporter):
	"""
	Makes the glue between the local file system and the :mod:`~syncacre.relay` and 
	:mod:`~syncacre.encryption` layers.

	This class manages the meta information, file modifications and sleep times.

	Attributes:

		repository (syncacre.manager.PermissionController): local file access controller.

		address (str): remote host address.

		directory (str): relative path to the repository on the remote host.

		encryption (syncacre.encryption.Cipher): encryption layer.

		relay (syncacre.relay.AbstractRelay): communication layer.

		timestamp (bool or str): if ``True`` (recommended), manages file modification times. 
			If `str`, in addition determines the timestamp format as supported by 
			:func:`time.strftime`.

		refresh (int): refresh interval in seconds.

		filetype (list of str): list of file extensions.

		pattern (str): regular expression to filter files by name.

		pop_args (dict): extra keyword arguments for 
			:meth:`~syncacre.relay.AbstractRelay.pop`.

	"""
	def __init__(self, relay, repository=None, address=None, directory=None, \
		encryption=Plain(None), timestamp=True, refresh=True, clientname=None, \
		filetype=[], pattern=None, quota=None, **relay_args):
		Reporter.__init__(self, **relay_args)
		self.repository = repository
		if not directory or directory[0] != '/':
			directory = '/' + directory
		self.directory = directory
		self.encryption = encryption
		if timestamp is True:
			timestamp = '%y%m%d_%H%M%S'
		self.timestamp = timestamp
		if isinstance(refresh, bool) and refresh:
			refresh = 30 # seconds
		self.refresh = refresh
		if filetype:
			self.filetype = [ f if f[0] == '.' else '.' + f
					for f in filetype ]
		else:
			self.filetype = []
		self.pattern = None
		if pattern:
			try:
				self.pattern = re.compile(pattern)
			except:
				self.logger.error("wrong filename pattern '%s'", pattern)
				self.logger.debug(traceback.format_exc())
		if isinstance(quota, tuple):
			value, unit = quota
			if unit:
				try:
					quota = value * storage_space_unit[unit]
				except KeyError:
					msg = "unsupported storage space unit '{}'".format(unit)
					self.logger.error(msg)
					#raise ValueError(msg)
					quota = None
			else:
				quota = value
		self.quota = quota
		self._quota_read_time = 0
		self.quota_read_interval = 300
		#self._max_space = None # attribute will be dynamically created
		self._used_space = None
		self.pop_args = {}
		if clientname:
			relay_args['client'] = clientname
		self.relay = relay(address, **relay_args)


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
		return self.directory


	def run(self):
		"""
		Runs the manager.

		Example:
		::

			from syncacre.manager import Manager
			from syncacre.relay   import WebDAV

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
		_last_error = None
		new = False
		while True:
			try:
				if _check_sanity:
					self.sanityCheck()
					_check_sanity = False
				if self.mode is None or self.mode == 'download':
					new |= self.download()
				if self.mode is None or self.mode == 'upload':
					new |= self.upload()
				if _fresh_start:
					if not new:
						self.logger.info('repository is up to date')
					_fresh_start = False
				if self.refresh:
					clock = Clock(self.refresh)
					clock.wait(self.logger)
				else:
					break
			except (KeyboardInterrupt, SystemExit) as e:
				_last_error = e
				break
			except UnrecoverableError as e:
				_last_error = e
				_last_trace = traceback.format_exc()
				break
			except Exception as e:
				t = time.time()
				if _last_error is None:
					_last_error = e
				elif type(e) == type(_last_error):
					if t - _last_error_time < 1: # the error is self-repeating too fast; abort
						break
				_last_error = e
				_last_error_time = t
				_last_trace = traceback.format_exc()
				self.logger.critical(_last_trace)
				_check_sanity = True # check again for corrupted files
		# close and clear everything
		try:
			self.relay.close()
		except:
			self.logger.error("cannot close the connection to '%s'", self.relay.address)
			self.logger.debug(traceback.format_exc())
		del self.relay # delete temporary files
		del self.encryption # delete temporary files
		# notify
		if not isinstance(_last_error, (KeyboardInterrupt, SystemExit)):
			# if last exception is not a keyboard interrupt
			if self.ui_controller is not None:
				self.ui_controller.notifyShutdown(_last_trace)
			if isinstance(_last_error, UnrecoverableError):
				self.logger.critical("unrecoverable error:")
				self.logger.critical(" %s", _last_error.args[0])
				self.logger.critical(" %s", _last_trace)
				self.logger.critical("the Python environment should be reset")
				raise _last_error # so that syncacre main process can signal the other processes


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
		if self.pattern:
			files = [ f for f in files if self.pattern.match(os.path.basename(f)) ]
		return files

	def sanityCheck(self):
		"""
		Performs sanity checks and fixes the corrupted files.
		"""
		for lock in self.relay.listCorrupted(self.dir):
			remote_file = os.path.relpath(lock.target, self.dir)
			local_file = self.repository.accessor(remote_file)
			self.logger.info("fixing uncompleted transfer: '%s'", remote_file)
			self.relay.repair(lock, local_file)

	def download(self):
		"""
		Finds out which files are to be downloaded and download them.
		"""
		remote = self.filter(self.relay.listReady(self.dir))
		new = False
		for filename in remote:
			local_file = self.repository.writable(filename)
			if not local_file:
				# update not allowed
				continue
			remote_file = join(self.dir, filename)
			last_modified = None
			if self.timestamp:
				meta = self.relay.getMetaInfo(remote_file)
				if meta:
					with open(meta, 'r') as f:
						last_modified = f.readline().rstrip()
					os.unlink(meta)
					last_modified = time.strptime(last_modified, self.timestamp)
					last_modified = calendar.timegm(last_modified) # remote_mtime
			if os.path.isfile(local_file):
				if last_modified and last_modified <= floor(os.path.getmtime(local_file)):
					# local_mtime = os.path.getmtime(local_file)
					continue
				msg = "updating local file '%s'"
			else:
				msg = "downloading file '%s'"
			new = True
			temp_file = self.encryption.prepare(local_file)
			self.logger.info(msg, filename)
			ok = self.relay.pop(remote_file, temp_file, blocking=False, **self.pop_args)
			if ok:
				self.logger.debug("file '%s' successfully downloaded", filename)
			elif ok is not None:
				self.logger.error("failed to download '%s'", filename)
			self.encryption.decrypt(temp_file, local_file)
			if last_modified:
				os.utime(local_file, (time.time(), last_modified))
		return new

	def upload(self):
		"""
		Finds out which files are to be uploaded and upload them.
		"""
		local = self.filter(self.localFiles())
		remote = self.relay.listTransfered(self.dir, end2end=False)
		new = False
		for local_file in local:
			filename = local_file[len(self.path):] # relative path
			if PYTHON_VERSION == 2 and isinstance(filename, unicode) and \
				remote and isinstance(remote[0], str):
				filename = filename.encode('utf-8')
			modified = False # if no remote copy, this is ignored
			if self.timestamp: # check file last modification time
				local_mtime = floor(os.path.getmtime(local_file))
				last_modified = time.gmtime(local_mtime) # UTC
				last_modified = time.strftime(self.timestamp, last_modified)
				if filename in remote:
					remote_file = join(self.dir, filename)
					meta = self.relay.getMetaInfo(remote_file)
					if meta:
						with open(meta, 'r') as f:
							remote_mtime = f.readline().rstrip()
						os.unlink(meta)
						if remote_mtime:
							remote_mtime = time.strptime(remote_mtime, self.timestamp)
							remote_mtime = calendar.timegm(remote_mtime)
							modified = remote_mtime < local_mtime
						else: # no meta information
							modified = True
							# this may not be true, but this will update the meta
							# information with a valid content.
					#else: (TODO) directly read mtime on remote copy?
			else:
				last_modified = None
			if filename not in remote or modified:
				new = True
				temp_file = self.encryption.encrypt(local_file)
				# check disk usage
				read_storage_space = True
				if self.quota_read_interval:
					t = time.time()
					read_storage_space = self.quota_read_interval < t - self._quota_read_time
					if read_storage_space:
						self._quota_read_time = t
				if read_storage_space:
					# update
					self._used_space, self._max_space = self.relay.storageSpace()
				ok = True
				if self._used_space is not None:
					if self.quota:
						if self._max_space:
							quota = min(self._max_space, self.quota)
						else:
							quota = self.quota
					if quota:
						additional_space = float(os.stat(temp_file).st_size)
						additional_space /= 1048576 # in MB
						expected = self._used_space + additional_space
						ok = expected < quota
						if ok:
							self._used_space = expected
				if ok:
					self.logger.info("uploading file '%s'", filename)
					ok = self.relay.push(temp_file, self.dir, \
						relative_path=filename, blocking=False, \
						last_modified=last_modified)
				else:
					self.logger.info("quota exceeded (used: %sMB of %sMB); no more files can be sent", round(used), round(quota))
				if ok:
					self.logger.debug("file '%s' successfully uploaded", filename)
				elif ok is not None:
					self.logger.warning("failed to upload '%s'", filename)
				self.encryption.finalize(temp_file) # delete encrypted copy
		return new

	def localFiles(self, path=None):
		"""
		Transitional method.

		Use ``self.repository.readableFiles`` instead.
		"""
		return self.repository.readableFiles(path)

