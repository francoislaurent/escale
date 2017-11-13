# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent
#   Contributions:
#     * `filetype` argument and attribute
#     * initial `filter` method (without `include` and `exclude` support)
#     * new placeholder format
#     * checksum function support

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
from escale.base.config import storage_space_unit
from escale.encryption.encryption import Plain
from .history import TimeQuotaController
from .cache import *
import hashlib


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

		checksum (str): hash algorithm name; see also the :mod:`hashlib` library.

		checksum_cache (bool or str or dict): path to a checksum cache file (str) or cache (dict) 
			of checksums for local files for relative filepaths as keys and 
			(last modification time, checksum) pairs as elements.
			If bool, then the cache path will be automatically determined.

		filetype (list of str): list of file extensions.

		include (list of str): regular expressions to include files by name.

		exclude (list of str): regular expressions to exclude files by name.

		tq_controller (escale.manager.TimeQuotaController): time and quota controller.

		count (int): puller count.

		includedirectory (list of str): regular expressions to include directories by name.

		excludedirectory (list of str): regular expressions to exclude directories by name.

		pop_args (dict): extra keyword arguments for 
			:meth:`~escale.relay.AbstractRelay.pop`.

	*new in 0.7.1:* `checksum_cache`

	"""
	def __init__(self, relay, repository=None, address=None, directory=None, \
		encryption=Plain(None), timestamp=True, refresh=True, clientname=None, \
		filetype=[], include=None, exclude=None, tq_controller=None, count=None, \
		checksum=True, checksum_cache=None, includedirectory=None, excludedirectory=None, \
		**relay_args):
		Reporter.__init__(self, **relay_args)
		self.repository = repository
		if directory:
			if directory[0] == '/':
				directory = directory[1:]
		else:
			directory = ''
		self.encryption = encryption
		self.timestamp = timestamp
		if checksum:
			if isinstance(checksum, (bool, int)):
				# poor default algorithm for compatibility with Python<3.6 clients
				checksum = 'sha512'
			def hash_function(data):
				h = hashlib.new(checksum)
				h.update(asbytes(data))
				return h.hexdigest()
			try:
				hashlib.new(checksum)
			except ValueError:
				self.logger.warning("unsupported hash algorithm: '%s'", checksum)
				self.logger.warning('checksum support deactivated')
				hash_function = None
			self.hash_function = hash_function
		else:
			self.hash_function = None
		if self.hash_function:
			if checksum_cache:
				if isinstance(checksum_cache, bool):
					self.logger.debug("Warning! The checksum cache will be loaded following Escale's default configuration file")
					checksum_cache = find_checksum_cache(self.repository.name)
				if isinstance(checksum_cache, basestring):
					self.checksum_cache = read_checksum_cache(checksum_cache)#ChecksumCache(checksum_cache)
				else:
					self.checksum_cache = checksum_cache
			else:
				self.checksum_cache = {}
		else:
			self.checksum_cache = None
		self.tq_controller = tq_controller
		if filetype:
			self.filetype = [ f if f[0] == '.' else '.' + f
					for f in filetype ]
		else:
			self.filetype = []
		self.include = None
		if include:
			if not isinstance(include, (tuple, list)):
				include = [ include ]
			self.include = []
			for exp in include:
				if exp[0] == '/':
					if exp[-1] == '/':
						exp = exp[1:-1]
					else:
						exp = exp[1:]
				else:
					exp = exp.replace('.', '\.').replace('*', '.*')
				try:
					
					self.include.append(re.compile(exp))
				except:
					self.logger.error("wrong filename pattern '%s'", exp)
					self.logger.debug(traceback.format_exc())
		self.exclude = None
		if exclude:
			if not isinstance(exclude, (tuple, list)):
				exclude = [ exclude ]
			self.exclude = []
			for exp in exclude:
				if exp[0] == '/':
					if exp[-1] == '/':
						exp = exp[1:-1]
					else:
						exp = exp[1:]
				else:
					exp = exp.replace('.', '\.').replace('*', '.*')
				try:
					
					self.exclude.append(re.compile(exp))
				except:
					self.logger.error("wrong filename pattern '%s'", exp)
					self.logger.debug(traceback.format_exc())
		self.include_directory = None
		if includedirectory:
			if not isinstance(includedirectory, (tuple, list)):
				includedirectory = [ includedirectory ]
			self.include_directory = []
			for exp in includedirectory:
				if exp[0] == '/':
					if exp[-1] == '/':
						exp = exp[1:-1]
					else:
						exp = exp[1:]
				else:
					exp = exp.replace('.', '\.').replace('*', '.*')
				try:
					
					self.include_directory.append(re.compile(exp))
				except:
					self.logger.error("wrong directory name pattern '%s'", exp)
					self.logger.debug(traceback.format_exc())
		self.exclude_directory = None
		if excludedirectory:
			if not isinstance(excludedirectory, (tuple, list)):
				excludedirectory = [ excludedirectory ]
			self.exclude_directory = []
			for exp in excludedirectory:
				if exp[0] == '/':
					if exp[-1] == '/':
						exp = exp[1:-1]
					else:
						exp = exp[1:]
				else:
					exp = exp.replace('.', '\.').replace('*', '.*')
				try:
					
					self.exclude_directory.append(re.compile(exp))
				except:
					self.logger.error("wrong directory name pattern '%s'", exp)
					self.logger.debug(traceback.format_exc())
		self.pop_args = {}
		arg_map = [('locktimeout', 'lock_timeout'),
			('maxpendingtransfers', 'max_pending_transfers')]
		for cfg_arg, rel_arg in arg_map:
			if cfg_arg in relay_args:
				relay_args[rel_arg] = relay_args.pop(cfg_arg)
		self.max_pending_transfers = relay_args.pop('max_pending_transfers', None)
		self.relay = relay(clientname, address, directory, **relay_args)
		if tq_controller is None:
			self.tq_controller = TimeQuotaController(refresh, logger=self.logger)
		self.tq_controller.quota_read_callback = self.relay.storageSpace
		if count:
			self.pop_args['placeholder'] = count


	#def __del__(self):
	#	if self.checksum_cache:
	#		if self.checksum_cache_file:
	#			self.logger.debug("saving checksum cache in '%s'", self.checksum_cache_file)
	#			write_checksum_cache(self.checksum_cache_file, self.checksum_cache, log=self.logger.debug)


	# transitional alias properties
	@property
	def path(self):
		return self.repository.path
	@property
	def mode(self):
		return self.repository.mode
	@mode.setter
	def mode(self, m):
		self.repository.mode = m
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
		while True:
			new = False
			try:
				self.remoteListing()
				if _check_sanity:
					self.sanityChecks()
					_check_sanity = False
				if self.mode != 'upload':
					new |= self.download()
				if self.mode != 'download':
					new |= self.upload()
				if _fresh_start:
					if not new:
						self.logger.info('repository is up to date')
					_fresh_start = False
				if new:
					self.logger.debug('reset adaptive timer')
					self.tq_controller.clock.reset()
				if not self.tq_controller.wait():
					break
			except ExpressInterrupt:
				raise
			except PostponeRequest as e:
				if e.args:
					self.logger.debug(*e.args)
				self.tq_controller.wait()
			except Exception as e:
				t = time.time()
				wait = False
				# break on fast self-repeating errors
				if 0 < _last_error_time and type(e) == type(last_error):
					# if _last_error_time is not 0, then last_error is defined
					if t - _last_error_time < 1: # the error repeats too fast; abort
						break
					else:
						wait = True
				last_error = e
				_last_error_time = t
				_check_sanity = True # check again for corrupted files
				# wait on network downtime
				if isinstance(e, OSError):
					# check errno; see also the errno standard library
					# a few candidates error codes:
					# ENETDOWN: 100, Network is down
					# ENETUNREACH: 101, Network is unreachable
					# ENETRESET: 102, Network dropped connection because of reset
					# ECONNABORTED: 103, Software caused connection abort
					# ECONNRESET: 104, Connection reset by peer
					# ENOTCONN: 107, Transport endpoint is not connected
					# ESHUTDOWN: 108, Cannot send after transport endpoint shutdown
					# ETIMEDOUT: 110, Connection timed out
					# EHOSTDOWN: 112, Host is down
					if e.args and e.args[0] in [104,107]:
						wait = True
				if wait:
					self.logger.debug("%s", e)
					self.tq_controller.wait()
				else:
					self.logger.critical(traceback.format_exc())
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
			files = [ f for f in files if any([ exp.match(os.path.basename(f)) for exp in self.include ]) ]
		if self.exclude:
			files = [ f for f in files if not any([ exp.match(os.path.basename(f)) for exp in self.exclude ]) ]
		if self.include_directory:
			files = [ f for f in files if any([ exp.match(os.path.dirname(f)) for exp in self.include_directory ]) ]
		if self.exclude_directory:
			files = [ f for f in files if not any([ exp.match(os.path.dirname(f)) for exp in self.exclude_directory ]) ]
		return files

	def _filter(self, f):
		"""
		Tell if a file is to be selected.

		Arguments:

			f (str): file basename.

		Returns:

			bool: ``True`` if selected, ``False`` if rejected.
		"""
		ok = True
		if self.filetype:
			ok = os.path.splitext(f)[1] in self.filetype
		if ok and self.include:
			ok = any([ exp.match(f) for exp in self.include ])
		if ok and self.exclude:
			ok = not any([ exp.match(f) for exp in self.exclude ])
		return ok

	def _filter_directory(self, dirname):
		"""
		Tell if a directory is to be crawled.

		Arguments:

			dirname (str): directory name (relative path).

		Returns:

			bool: ``True`` if selected, ``False`` if rejected.
		"""
		ok = True
		if ok and self.include_directory:
			ok = any([ exp.match(dirname) for exp in self.include_directory ])
		if ok and self.exclude_directory:
			ok = not any([ exp.match(dirname) for exp in self.exclude_directory ])
		return ok

	def sanityChecks(self):
		"""
		Performs sanity checks and fixes the corrupted files.
		"""
		for lock in self.relay.listCorrupted():
			# `resource` and `remote_file` are synonym
			remote_file = lock.target
			if remote_file:
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
			resource = remote_file
			local_file = self.repository.writable(resource, absolute=True)
			if not local_file:
				# update not allowed
				continue
			meta = self.relay.getMetadata(remote_file, timestamp_format=self.timestamp)
			last_modified = None
			if self.timestamp:
				if meta and meta.timestamp:
					last_modified = meta.timestamp
				else:
					# if `timestamp` is `True` or is a format string,
					# then metadata should be defined
					self.logger.warning("corrupt meta information for file '%s'", remote_file)
			if os.path.isfile(local_file):
				# generate checksum of the local file
				checksum = self.checksum(resource)
				# check for modifications
				if not meta:
					self.logger.info("missing meta information for file '%s'; deleting file", remote_file)
					self.relay.delete(remote_file)
					continue
				elif not meta.fileModified(local_file, checksum, remote=True, debug=self.logger.debug):
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
			with self.repository.confirmPull(resource):
				new = True
				temp_file = self.encryption.prepare(local_file)
				self.logger.info(msg, resource)
				try:
					with self.tq_controller.pull(temp_file):
						ok = self.relay.pop(remote_file, temp_file, blocking=False, **self.pop_args)
					if not ok:
						raise RuntimeError
				except RuntimeError: # TODO: define specific exceptions
					ok = False
				if ok:
					self.logger.debug("file '%s' successfully downloaded", resource)
				elif ok is not None:
					self.logger.error("failed to download '%s'", resource)
					continue
				self.encryption.decrypt(temp_file, local_file)
				if last_modified:
					# handle delay on file creation
					first_time = True
					while not os.path.exists(local_file):
						if first_time:
							self.logger.debug('local file not ready: %s', local_file)
							first_time = False
					# set last modification time
					os.utime(local_file, (time.time(), last_modified))
		return new

	def upload(self):
		"""
		Finds out which files are to be uploaded and upload them.
		"""
		new = False
		if self.max_pending_transfers:
			if self.max_pending_transfers <= self.relay.listReady():
				return new
		local = self.localFiles()
		remote = self.relay.listTransferred('', end2end=False)
		for resource in local:
			remote_file = resource
			local_file = self.repository.absolute(resource)
			if PYTHON_VERSION == 2 and isinstance(remote_file, unicode) and \
				remote and isinstance(remote[0], str):
				remote_file = remote_file.encode('utf-8')
			checksum = self.checksum(resource)
			modified = False # if no remote copy, this is ignored
			exists = remote_file in remote
			if (self.timestamp or self.hash_function) and exists:
				# check file last modification time and checksum
				meta = self.relay.getMetadata(remote_file, timestamp_format=self.timestamp)
				if meta:
					modified = meta.fileModified(local_file, checksum, remote=False, debug=self.logger.debug)
				else:
					# no meta information available
					modified = True
					# this may not be true, but this will update the meta
					# information with a valid content.
			if not exists or modified:
				with self.repository.confirmPush(resource):
					new = True
					last_modified = os.path.getmtime(local_file)
					temp_file = self.encryption.encrypt(local_file)
					self.logger.info("uploading file '%s'", resource)
					try:
						with self.tq_controller.push(local_file):
							ok = self.relay.push(temp_file, remote_file, blocking=False,
								last_modified=last_modified, checksum=checksum)
					except QuotaExceeded as e:
						self.logger.info("%s; no more files can be sent", e)
						ok = False
					finally:
						self.encryption.finalize(temp_file)
					if ok:
						self.logger.debug("file '%s' successfully uploaded", resource)
					elif ok is not None:
						self.logger.warning("failed to upload '%s'", resource)
		return new

	def localFiles(self, path=None):
		"""
		Transitional method.

		Use ``self.repository.readableFiles`` instead.
		"""
		return self.repository.readable(self.repository.listFiles(path,
				dirname=self._filter_directory, basename=self._filter), \
			unsafe=True)

	def checksum(self, resource):
		# `resource` should be a relative path!
		local_file = self.repository.absolute(resource)
		checksum = None
		if self.checksum_cache is not None:
			mtime = int(os.path.getmtime(local_file))
			try:
				previous_mtime, checksum = self.checksum_cache[resource]
			except KeyError:
				pass
			else:
				if previous_mtime != mtime:
					# calculate the checksum again
					checksum = None
		if not checksum and self.hash_function:
			with open(local_file, 'rb') as f:
				checksum = self.hash_function(f.read())
			if self.checksum_cache is not None:
				#self.logger.debug('\n'.join((
				#	"caching checksum for file:",
				#	"'{}'",
				#	"last modified: {}",
				#	"checksum: {}")).format(local_file, mtime, checksum))
				self.checksum_cache[resource] = (mtime, checksum)
		return checksum

	def remoteListing(self):
		t = time.time()
		self.relay.remoteListing()
		dur = time.time() - t
		if 10 < dur:
			msg = 'remote repository crawled in {:.0f} seconds'.format(dur)
			self.logger.debug(msg)

