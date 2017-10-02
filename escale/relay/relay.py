# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


import os
import sys
import time
import calendar
import tempfile
import logging

from escale.base.essential import *
from .info import *
from escale.log import log_root
from escale.base.exceptions import *



def with_path(path, fun, *args, **kwargs):
	"""
	Helper function that applies a string manipulation function to the filename part of a path.
	"""
	_dir, _file = os.path.split(path)
	return os.path.join(_dir, fun(_file, *args, **kwargs))



class AbstractRelay(Reporter):
	"""
	Send files to/from a remote host.

	This class is an interface that groups together the methods called by 
	:class:`escale.manager.Manager`.

	Attributes:

		client (str): client identifier.

		address (str): address of the remote host.

		repository (str): path of the repository on the remote host.

	"""
	__slots__ = ['client', 'address', 'repository']

	def __init__(self, client, address, repository, logger=None, ui_controller=None):
		Reporter.__init__(self, logger=logger, ui_controller=ui_controller)
		self.client = client
		self.address = address
		self.repository = repository

	def open(self):
		"""
		Establish the connection with the remote host.

		Returns:

			bool: True if successful, False if failed.
		"""
		raise NotImplementedError('abstract method')

	def storageSpace(self):
		"""
		Query for how much space is available on the remote host.

		Returns:

			(int or float, int or None):
			first argument is available space in megabytes (MB),
			second argument is disk quota in megabytes (MB).
		"""
		raise NotImplementedError('abstract method')

	def remoteListing(self):
		"""
		Crawl the relay repository for later calls to `list*` methods.

		`remoteListing` should be optional and all the `list*` methods
		should work with or without past calls to this method.
		"""
		raise NotImplementedError

	def listReady(self, remote_dir='', recursive=True):
		"""
		List the files on the remote host that are ready for download.
		All paths are relative to the repository root.

		Arguments:

			remote_dir (str): remote directory to "ls".

			recursive (bool): whether to list subdirectories or not.

		Returns:

			list of str: list of paths.
		"""
		raise NotImplementedError('abstract method')

	def listCorrupted(self, remote_dir='', recursive=True):
		"""
		List the files on the remote host that are corrupted.
		All paths are relative to the repository root.

		Corrupted files are files with a lock owned by `self`, as identified
		by the `client` attribute.
		If `client` evaluates to ``False``, corrupted files are returned
		as an empty list.

		Corrupted files are represented by the unreleased locks.

		Arguments:

			remote_dir (str): remote directory to "ls".

			recursive (bool): whether to list subdirectories or not.

		Returns:

			list of LockInfo: list of locks.
		"""
		if self.client:
			raise NotImplementedError('abstract method')
		else:
			return []

	def listTransferred(self, remote_dir='', end2end=True, recursive=True):
		"""
		List the files on the remote host that have been transferred.
		All paths are relative to the repository root.

		Arguments:

			remote_dir (str): remote directory to "ls".

			end2end (bool): if True, list only files which content is no 
				longer available on the remote host.

			recursive (bool): whether to list subdirectories or not.

		Returns:

			list of str: list of paths.
		"""
		raise NotImplementedError('abstract method')

	def getMetadata(self, remote_file, output_file=None, timestamp_format=None):
		"""
		Download meta-information.

		If no local file is specified but `output_file` is `True`, 
		`getMetadata` makes and returns a temporary file instead of a
		:class:`~escale.relay.info.Metadata` object.

		The returned temporary file should be manually unlinked 
		once done with it.

		Example:

		.. code-block:: python

			import os

			temporary_file = relay.getMetadata(path_to_remote_file, output_file=True)

			with open(temporary_file, 'r') as f:
				# do something with `f`

			os.unlink(temporary_file)

		
		Arguments:

			remote_file (str): path to regular file (no placeholder or message).

			output_file (str or bool): path to local file.

			timestamp_format (str): backward-compatibility option for the former
				metadata format.

		Returns:

			Metadata or str: metadata or path of a local file.

		*in 0.5.1:* *getMetaInfo* renamed as `getMetadata`

		*new in 0.5.1:* timestamp_format; `getMetadata` returns a `Metadata` object
		"""
		raise NotImplementedError('abstract method')

	def push(self, local_file, remote_dest, last_modified=None, checksum=None, blocking=True):
		"""
		Upload a file to the remote host.

		Arguments:

			local_file (str): path to the local file to be sent.

			remote_dest (str): path to the target remote file.

			last_modified (str): meta information to be recorded for the remote copy.

			checksum (str-like): checksum of the encrypted content of `local_file`.

			blocking (bool): if target exists and is locked, whether should we block 
				until the lock is released or skip the file.

		Returns:

			bool: True if successful, False if failed.

		*new in 0.5.1:* checksum
		"""
		raise NotImplementedError('abstract method')

	def pop(self, remote_file, local_dest, placeholder=True, blocking=True, **kwargs):
		"""
		Download a file from the remote host and unlinks remote copy if relevant.

		Arguments:

			remote_file (str): relative path to the remote file.

			local_dest (str): path to the target local file.

			placeholder (bool or int): whether to generate a placeholder file.
				If an int is given, it specifies the number of pullers (downloading
				clients).

			blocking (bool): if target exists and is locked, whether should we block 
				until the lock is released or skip the file.

		Returns:

			bool: True if successful, False if failed.
		"""
		raise NotImplementedError('abstract method')

	def delete(self, remote_file):
		"""
		Fake download and delete a remote file.

		This operation should mimic `pop` but deletes the remote file instead of
		downloading it.

		Arguments:

			remote_file (str): relative path to the remote file.

		Returns:

			bool: True if successful, False if failed.
		"""
		raise NotImplementedError('abstract method')

	def repair(self, lock, local_file, checksum=None):
		"""
		Attempt to repair a corrupted file.

		Arguments:

			lock (LockInfo): lock information for the corrupted file; the `target`
				attribute refers to the file on the remote host.

			local_file (escale.manager.Accessor): accessor for local file.

			checksum (str-like): checksum of the encrypted content of `local_file`.

		*new in 0.5.1:* checksum
		"""
		raise NotImplementedError('abstract method')

	def purge(self, remote_dest=''):
		"""
		Delete a remote directory or collection, and its content.

		This method is called by test routines with default argument to purge the
		entire repository on the relay host.

		Arguments:

			remote_dir (str): path to the remote directory to be removed.

		"""
		raise NotImplementedError('abstract method')

	def close(self):
		"""
		Close the connection with the remote host.

		Returns:

			bool: True if successful, False if failed.
		"""
		raise NotImplementedError('abstract method')



class Relay(AbstractRelay):
	"""
	Send files to/from a remote relay.

	This class is a partial implementation of :class:`AbstractRelay`.
	Especially, it implements independent placeholders and locks.

	Placeholders and locks are named after the corresponding regular files.
	Extra strings are prepended and appended to the regular filename.

	Messages are similar to placeholders and locks. They act as actual
	placeholders for regular files when these regular files have to be
	deleted before they could be downloaded by all the pullers.

	Messages are an experimental feature and the clearing mechanism is
	not fully implemented yet.

	Placeholders, locks and messages are represented as filenames.
	They can be referred to as special files, while transferred files
	are referred to as regular files.

	Any derivative class should implement:

	* :meth:`_list`
	* :meth:`hasPlaceholder` and :meth:`hasLock`
	* :meth:`_push` and either:

		* :meth:`_get`
		* :meth:`_pop` with `_unlink` optional argument
		* both :meth:`_get` and :meth:`_pop`

	* :meth:`delete`, necessary for tests

	Attributes:

		_temporary_file (list): list of paths to existing temporary files.

		_placeholder_prefix (str): prefix for placeholder files.

		_placeholder_suffix (str): suffix for placeholder files.

		_lock_prefix (str): prefix for lock files.

		_lock_suffix (str): suffix for lock files.

		lock_timeout (bool or int): maximum age of an unclaimed lock in seconds.

		_message_hash (function or None): generates a message subextension (`str`);
			takes the path to the corresponding local regular file as input argument (`str`);
			a subextension should not contain *'.'*.

		_message_prefix (str): prefix for message files.

		_message_suffix (str): suffix for message files.

		placeholder_cache (dict): dictionnary of cached placeholders.

	*new in 0.5.1:* placeholder_cache
	"""
	__slots__ = [ '_temporary_files',
		'_placeholder_prefix', '_placeholder_suffix',
		'_lock_prefix', '_lock_suffix', 'lock_timeout',
		'_message_hash', '_message_prefix', '_message_suffix',
		'placeholder_cache', 'listing_cache']

	def __init__(self, client, address, repository, logger=None, ui_controller=None,
			lock_timeout=True, timestamped_messages=False, **ignored):
		AbstractRelay.__init__(self, client, address, repository,
				logger=logger, ui_controller=ui_controller)
		if self.logger is None:
			if client:
				self.logger = logging.getLogger(log_root).getChild(client)
			else:
				self.logger = logging.getLogger(log_root).getChild(address)
		self._temporary_files = []
		self._placeholder_prefix = '.'
		self._placeholder_suffix = '.placeholder'
		self._lock_prefix = '.'
		self._lock_suffix = '.lock'
		if isinstance(lock_timeout, bool) and lock_timeout:
			self.lock_timeout = 3600
		else:
			self.lock_timeout = lock_timeout
		self._message_prefix = '.'
		self._message_suffix = '.message'
		if timestamped_messages:
			def message_hash(path):
				return time.strftime('%y%m%d%H%M%S', time.gmtime())
			self._message_hash = message_hash
		else:
			self._message_hash = None
		self.placeholder_cache = {}
		self.listing_cache = None


	def newTemporaryFile(self):
		'''
		Make a new temporary file.

		Returns:

			str: path to temporary file.
		'''
		fd, name = tempfile.mkstemp()
		os.close(fd)
		self._temporary_files.append(name)
		return name

	def delTemporaryFile(self, f):
		'''
		Delete an existing temporary file.

		Arguments:

			file (str): path to temporary file.
		'''
		try:
			os.unlink(f)
		except OSError:
			pass
		try:
			self._temporary_files.remove(f)
		except ValueError:
			pass

	def __del__(self):
		for f in self._temporary_files:
			try:
				os.unlink(f)
			except OSError:
				pass


	def _placeholder(self, filename):
		return '{}{}{}'.format(self._placeholder_prefix, filename, self._placeholder_suffix)

	def _lock(self, filename):
		return '{}{}{}'.format(self._lock_prefix, filename, self._lock_suffix)

	def _isPlaceholder(self, filename):
		return filename.startswith(self._placeholder_prefix) \
			and filename.endswith(self._placeholder_suffix)

	def _isLock(self, filename):
		return filename.startswith(self._lock_prefix) \
			and filename.endswith(self._lock_suffix)

	def _fromPlaceholder(self, filename):
		if self._placeholder_suffix:
			end = -len(self._placeholder_suffix)
		else:
			end = None
		return filename[len(self._placeholder_prefix):end]

	def _fromLock(self, filename):
		if self._lock_suffix:
			end = -len(self._lock_suffix)
		else:
			end = None
		return filename[len(self._lock_prefix):end]

	def _safePlaceholder(self, filename):
		if self._isPlaceholder(filename):
			return filename
		else:
			return self._placeholder(filename)

	def _safeLock(self, filename):
		if self._isLock(filename):
			return filename
		else:
			return self._lock(filename)

	def placeholder(self, path):
		return with_path(path, self._safePlaceholder)

	def lock(self, path):
		return with_path(path, self._safeLock)

	def isPlaceholder(self, path):
		return self._isPlaceholder(os.path.basename(path))

	def isLock(self, path):
		return self._isLock(os.path.basename(path))

	def fromPlaceholder(self, path):
		return with_path(path, self._fromPlaceholder)

	def fromLock(self, path):
		return with_path(path, self._fromLock)


	def _isMessage(self, filename):
		return filename.startswith(self._message_prefix) \
			and filename.endswith(self._message_suffix)

	def isMessage(self, path):
		return self._isMessage(os.path.basename(path))

	def _message(self, filename, filepath):
		if self.message_hash is None:
			return '{}{}{}'.format(self._message_prefix, filename, self._message_suffix)
		else:
			_hash = self.message_hash(filepath)
			if '.' in _hash:
				raise ValueError("'.' in message hash")
			return '{}{}.{}{}'.format(self._message_prefix, filename,
					_hash, self._message_suffix)

	def _safeMessage(self, filename, filepath):
		if self._isMessage(filename):
			return filename
		else:
			return self._message(filename, filepath)

	def message(self, path):
		_dir, _file = os.path.split(path)
		return os.path.join(_dir, self._safeMessage(_file, path))

	def _fromMessage(self, filename):
		if self._message_suffix:
			end = -len(self._message_suffix)
		else:
			end = None
		message = filename[len(self._message_prefix):end]
		if self._message_hash is not None:
			message = message[::-1].split('.', 1)[1][::-1]
		return message

	def fromMessage(self, path):
		return with_path(path, self._fromMessage)


	def _isSpecial(self, filename):
		return self._isLock(filename) \
			or self._isPlaceholder(filename) \
			or self._isMessage(filename)

	def isSpecial(self, path):
		return self._isSpecial(os.path.basename(path))

	def _fromSpecial(self, filename):
		if self._isLock(filename):
			return self._fromLock(filename)
		elif self._isPlaceholder(filename):
			return self._fromPlaceholder(filename)
		elif self._isMessage(filename):
			return self._fromMessage(filename)
		else:
			raise ValueError("'%s' is not a valid special filename".format(filename))

	def fromSpecial(self, path):
		return with_path(path, self._fromSpecial)


	def open(self):
		pass

	def close(self):
		pass

	def storageSpace(self):
		# TODO: default implementation with `size`
		return (None, None)

	def _list(self, remote_dir='', recursive=True, stats=[]):
		"""
		List all files, including hidden files, relative to `remote_dir`.
		All paths are relative to the repository root.

		Arguments:

			remote_dir (str): directory on the remote host.

			recursive (bool): if ``True``, list files in subdirectories as well.

			stats (list): can be `[ 'mtime' ]`.

		Returns:

			iterator or list of str: list of paths.

		"""
		raise NotImplementedError('abstract method')

	def remoteListing(self):
		self.listing_cache = list(self._list('', recursive=True, stats=('mtime',)))

	def listReady(self, remote_dir='', recursive=True):
		"""
		The default implementation manipulates placeholders and locks as individual files.

		It caches last modification times of placeholders for future `getMetadata` calls.
		"""
		if remote_dir or (self.listing_cache is None):
			ls = self._list(remote_dir, recursive=recursive, stats=('mtime',))
		else:
			ls = self.listing_cache
		if not ls:
			return []
		lock_files = []
		regular_files = []
		for file, mtime in ls:
			filedir, filename = os.path.split(file)
			if self._isLock(filename):
				lock_files.append(file)
			elif self._isPlaceholder(filename):
				if mtime:
					regular_file = os.path.join(filedir, self._fromPlaceholder(filename))
					try:
						previous_mtime, meta = self.placeholder_cache[regular_file]
						if previous_mtime < mtime:
							meta = None
					except KeyError:
						meta = None
					self.placeholder_cache[regular_file] = (mtime, meta)
			elif not filename.startswith('.'):#self._isMessage(filename):
				lock_file = join(filedir, self._lock(filename))
				regular_files.append((file, lock_file))
		ready = [ regular_file
				for regular_file, lock_file in regular_files
				if lock_file not in lock_files ]
		return ready

	def listCorrupted(self, remote_dir='', recursive=True):
		"""
		The default implementation manipulates locks as individual files.
		"""
		if not (self.client or self.lock_timeout):
			return []
		if remote_dir or (self.listing_cache is None):
			ls = self._list(remote_dir, recursive=recursive, stats=['mtime'])
		else:
			ls = self.listing_cache
		locks = []
		for file, mtime in ls:
			if self.isLock(file):
				lock = self.getLockInfo(join(remote_dir, self.fromLock(file)))
				if lock.owner:
					if lock.owner == self.client:
						locks.append(lock)
				elif mtime and self.lock_timeout:
					if isinstance(mtime, time.struct_time):
						# for backward compatibility
						mtime = calendar.timegm(mtime)
					if self.lock_timeout < time.time() - mtime:
						locks.append(lock)
		return locks

	def listTransferred(self, remote_dir='', end2end=True, recursive=True):
		"""
		The default implementation manipulates placeholders and locks as individual files.
		"""
		if remote_dir or (self.listing_cache is None):
			ls = self._list(remote_dir, recursive=recursive, stats=('mtime',))
		else:
			ls = self.listing_cache
		if not ls:
			return []
		regular_files = []
		placeholders = []
		others = []
		for file, mtime in ls:
			filedir, filename = os.path.split(file)
			if self._isPlaceholder(filename):
				regular_file = os.path.join(filedir, self._fromPlaceholder(filename))
				placeholders.append(regular_file)
				if mtime:
					try:
						previous_mtime, meta = self.placeholder_cache[regular_file]
						if previous_mtime < mtime:
							meta = None
					except KeyError:
						meta = None
					self.placeholder_cache[regular_file] = (mtime, meta)
			else:
				others.append(file)
		ls = others
		if end2end:
			return placeholders
		else:
			locks = []
			others = []
			for file in ls:
				if self.isLock(file):
					locks.append(self.fromLock(file))
				elif not file.startswith('.'):
					others.append(file)
			return others + placeholders + locks

	def size(self, remote_file):
		"""
		Size of a file in bytes.

		If the file does not exist, return ``None`` instead.

		Arguments:

			remote_file (str): relative path to a file on the remote host.

		Returns:

			int or None: file size in bytes.

		"""
		raise NotImplementedError('abstract method')

	def touch(self, remote_file, content=None):
		"""
		Create an empty file.

		.. warning:: this is different from Unix *touch* and overwrites 
			existing files instead of updating the last access time attribute.
		"""
		#local_file = self.newTemporaryFile()
		f, local_file = tempfile.mkstemp(text=True)
		# f is an open file descriptor in 'w' mode and can be manipulated 
		# with os.write/os.close functions
		try:
			with os.fdopen(f, 'w') as f: # convert f into a file object
				if content:
					if isinstance(content, list):
						nlines = len(content)
						for lineno, line in enumerate(content):
							f.write(asstr(line))
							if lineno + 1 < nlines:
								f.write('\n')
					else:
						f.write(asstr(content))
			self._push(local_file, remote_file)
		finally:
			os.unlink(local_file)
		#self.delTemporaryFile(local_file)

	def unlink(self, remote_file):
		"""
		`unlink` should raise an error on deleting missing files.

		This implementation relies on `_pop`. 
		As a consequence `_pop` should raise an error on trying to get a missing file.
		"""
		#trash = self.newTemporaryFile()
		fd, trash = tempfile.mkstemp()
		os.close(fd)
		try:
			if isinstance(remote_file, list):
				for file in remote_file:
					self._pop(file, trash)
			else:
				self._pop(remote_file, trash)
		finally:
			os.unlink(trash)
		#self.delTemporaryFile(trash)

	def hasPlaceholder(self, remote_file):
		"""
		Checks for placeholder presence.

		The default implementation manipulates placeholders as individual files.

		Arguments:

			remote_file (str): relative path to a regular file on the remote host.

		Returns:

			bool: ``True`` if there exists a placeholder for `remote_file`, 
				``False`` otherwise.

		"""
		dirname, filename = os.path.split(remote_file)
		return self.exists(self._placeholder(filename), dirname=dirname)

	def hasLock(self, remote_file):
		"""
		Checks for lock presence.

		The default implementation manipulates locks as individual files.

		Arguments:

			remote_file (str): relative path to a regular file on the remote host.

		Returns:

			bool: ``True`` if there exists a lock for `remote_file`, 
				``False`` otherwise.

		"""
		dirname, filename = os.path.split(remote_file)
		return self.exists(self._lock(filename), dirname=dirname)

	def getLockInfo(self, remote_file):
		"""
		This method treats locks as files.
		"""
		remote_lock = self.lock(remote_file)
		fd, local_lock = tempfile.mkstemp()
		os.close(fd)
		try:
			self._get(remote_lock, local_lock)
		except ExpressInterrupt:
			raise
		except:
			info = LockInfo()
		else:
			info = parse_lock_file(local_lock, target=remote_file)
		finally:
			os.unlink(local_lock)
		return info

	def getMetadata(self, remote_file, output_file=None, timestamp_format=None):
		"""
		This method treats placeholders as files.
		"""
		if self.hasPlaceholder(remote_file):
			ts, meta = self.placeholder_cache.get(remote_file, (None, None))
			if output_file is True or meta is None:
				local_placeholder = self.newTemporaryFile()
			elif output_file:
				local_placeholder = output_file
			if meta is None:
				remote_placeholder = self.placeholder(remote_file)
				self._get(remote_placeholder, local_placeholder)
				if ts or not output_file:
					meta = parse_metadata(local_placeholder, \
							target=remote_file, \
							log=self.logger.debug, \
							timestamp_format=timestamp_format)
					if ts:
						self.placeholder_cache[remote_file] = (ts, meta)
					else:#elif not output_file:
						self.delTemporaryFile(local_placeholder)
			elif output_file:
				with open(local_placeholder, 'wb') as f:
					f.write(repr(meta))
			if output_file:
				meta = local_placeholder
			return meta
		else:
			if self.placeholder_cache:
				try:
					del self.placeholder_cache[remote_file]
				except KeyError:
					pass
			return None

	def updatePlaceholder(self, remote_file, last_modified=None, checksum=None):
		"""
		Update a placeholder when the corresponding file is pushed.

		This method treats placeholders as files.

		To pop or get a file, use :meth:`markAsRead` instead.

		*new in 0.5.1:* checksum
		"""
		meta = Metadata(pusher=self.client, target=remote_file,
				timestamp=last_modified, checksum=checksum)
		self.touch(self.placeholder(remote_file), repr(meta))

	def releasePlace(self, remote_file, handle_missing=False):
		"""
		This method treats placeholders as files.
		"""
		try:
			self.unlink(self.placeholder(remote_file))
		except ExpressInterrupt:
			raise
		except: # not found?
			msg = ("error while releasing place for file: '%s'", remote_file)
			if handle_missing:
				self.logger.debug(*msg)
			else:
				self.logger.warning(*msg)
				raise

	def acquireLock(self, remote_file, mode=None, blocking=True):
		"""
		This method treats locks as files.
		"""
		if blocking:
			if blocking is True: # if not numerical
				blocking = 60 # translate it to time, in seconds
			while self.hasLock(remote_file):
				self.logger.debug('lock not available; waiting %s seconds', blocking)
				time.sleep(blocking)
		elif self.hasLock(remote_file):
			return False
		lock_info = LockInfo(owner=self.client, mode=mode)
		self.touch(self.lock(remote_file), content=repr(lock_info))
		return True

	def releaseLock(self, remote_file):
		"""
		This method treats locks as files.
		"""
		self.unlink(self.lock(remote_file))

	def _push(self, local_file, remote_dest):
		"""
		Send a local file to the remote host.

		Arguments:

			local_file (str): path to a local file.

			remote_dest (str): path to a file on the remote host.

		Returns:

			bool or nothing: ``True`` if transfer was successful, ``False`` otherwise.

		"""
		raise NotImplementedError('abstract method')

	def push(self, local_file, remote_dest, last_modified=None, checksum=None, blocking=True):
		if not self.acquireLock(remote_dest, mode='w', blocking=blocking):
			return False
		if last_modified:
			self.updatePlaceholder(remote_dest, last_modified=last_modified, checksum=checksum)
		self._push(local_file, remote_dest)
		self.releaseLock(remote_dest)
		return True

	def _pop(self, remote_file, local_dest, makedirs=True):
		"""
		Download a file and delete it from the remote host.

		.. note:: :meth:`_pop` can be implemented with an extra `_unlink` keyword argument
			that is not supported by default and makes the default implementation for
			:meth:`_get` valid.

		Arguments:

			remote_file (str): path to a file on the remote host.

			local_dest (str): path to a local directory.

			makedirs (bool): make directories if missing.

			_unlink (bool, optional): if ``False``, do not delete the file from the 
				remote host. This keyword argument may not be recognized at all!

		Returns:

			bool or nothing: ``True`` if transfer was successful, ``False`` otherwise.

		"""
		self._get(remote_file, local_dest, makedirs)
		self.unlink(remote_file)

	def _get(self, remote_file, local_dest, makedirs=True):
		"""
		Download a file and do NOT delete it from the remote host.

		Arguments:

			remote_file (str): path to a file on the remote host.

			local_dest (str): path to a local directory.

			makedirs (bool): make directories if missing.

		Returns:

			bool or nothing: ``True`` if transfer was successful, ``False`` otherwise.

		"""
		self._pop(remote_file, local_dest, makedirs=makedirs, _unlink=False)

	def pop(self, remote_file, local_dest, placeholder=True, blocking=True, **kwargs):
		# TODO: ensure that local_dest is a path to a file and not a directory
		if not self.acquireLock(remote_file, mode='r', blocking=blocking):
			return False
		let = False
		if placeholder:
			has_placeholder = self.hasPlaceholder(remote_file)
			if has_placeholder and 1 < placeholder:
				remote_placeholder = self.placeholder(remote_file)
				local_placeholder = self.newTemporaryFile()
				kwargs['local_placeholder'] = local_placeholder
				self._get(remote_placeholder, local_placeholder)
				with open(local_placeholder, 'r') as f:
					nreads = len(f.readlines()) - 1
				let = nreads < placeholder - 1
		if let:
			self._get(remote_file, local_dest)
		else:
			self._pop(remote_file, local_dest)
		if placeholder:
			if has_placeholder:
				self.markAsRead(remote_file, **kwargs)
				if 1 < placeholder: # or similarly: if 'local_placeholder' in kwargs:
					self.delTemporaryFile(local_placeholder)
			else: # older-than-old style placeholding mechanism
				# could have warned before getting the file
				self.logger.warning("missing meta information for file: '%s'", remote_file)
				# no modification time or checksum
				self.updatePlaceholder(remote_file)
		self.releaseLock(remote_file)
		return True

	def get(self, remote_file, local_dest, placeholder=True, blocking=True, **kwargs):
		# TODO: ensure that local_dest is a path to a file and not a directory
		if not self.acquireLock(remote_file, mode='r', blocking=blocking):
			return False
		self._get(remote_file, local_dest)
		if placeholder and self.hasPlaceholder(remote_file):
			self.markAsRead(remote_file, **kwargs)
		self.releaseLock(remote_file)
		return True

	def markAsRead(self, remote_file, local_placeholder=None):
		"""
		This method treats placeholders as files.

		Compatible with both old-style and new-style placeholders.
		"""
		remote_placeholder = self.placeholder(remote_file)
		get = not local_placeholder
		if get:
			local_placeholder = self.newTemporaryFile()
			self._get(remote_placeholder, local_placeholder)
			with open(local_placeholder, 'a') as f:
				f.write('\n{}'.format(self.client))
		self._push(local_placeholder, remote_placeholder)
		if get:
			self.delTemporaryFile(local_placeholder)

	def exists(self, filename, dirname=None):
		if not dirname:
			dirname, filename = os.path.split(filename)
		return filename in self._list(dirname, recursive=False)

	def delete(self, remote_file, blocking=True, **kwargs):
		if not self.acquireLock(remote_file, mode='r', blocking=blocking):
			return False
		self.unlink(remote_file)
		try:
			self.markAsRead(remote_file, **kwargs)
		except NotImplementedError:
			pass
		self.releaseLock(remote_file)
		return True

	def repair(self, lock, local_file, checksum=None):
		# TODO: use the checksum to resolve conflicting situations
		remote_file = lock.target
		if lock.mode == 'w':
			if not local_file.exists():
				self.logger.error("could not find local file")# '%s'", local_file)
				self.logger.debug("clearing related remote files")
				# this is actually the default behavior
			if self.exists(remote_file):
				# do not take any risk; size is not a reliable indicator
				#remote_size = self.size(remote_file)
				#local_size = local_file.size()
				#if remote_size != local_size:
					self.unlink(remote_file)
			# delete the placeholder to send the file again
			self.releasePlace(remote_file, True)
		elif lock.mode == 'r':
			if local_file.exists():
				# TODO: check modification time
				# do not take any risk; size is not a reliable indicator
				#remote_size = self.size(remote_file)
				#if remote_size is not None:
				#	local_size = local_file.size()
				#	if local_size != remote_size:
						local_file.delete()
			if not self.exists(remote_file):
						# delete the placeholder to request the file again
						self.releasePlace(remote_file, True)
		else: # old-style lock?
			if self.exists(remote_file):
				self.unlink(remote_file)
			self.releasePlace(remote_file, True)
		# release the lock
		self.releaseLock(remote_file)



class IRelay(Relay):
	"""
	Extend :class:`Relay` with alternative implementation for :meth:`hasPlaceholder` and 
	:meth:`hasLock`.

	This class is useful if placeholders (respectively locks) are available together in 
	a list.

	"I" stands for "individual" because placeholders and locks are individual entities
	and can be manipulated as a file, in addition to be records in a list.

	The :meth:`listPlaceholders` and :meth:`listLocks` methods should be overloaded.

	"""
	def listPlaceholders(self, remote_dir):
		"""
		List placeholders.

		Arguments:

			remote_dir (str): path to a remote directory.

		Returns:

			list of str: list of paths to placeholders.
		"""
		ls = self._list(remote_dir, recursive=False)
		return [ file for file in ls if self.isPlaceholder(file) ]

	def listLocks(self, remote_dir):
		"""
		List locks.

		Arguments:

			remote_dir (str): path to a remote directory.

		Returns:

			list of str: list of paths to locks.
		"""
		ls = self._list(remote_dir, recursive=False)
		return [ file for file in ls if self.isLock(file) ]

	def hasPlaceholder(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return self._placeholder(filename) in self.listPlaceholders(remote_dir)

	def hasLock(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return self._lock(filename) in self.listLocks(remote_dir)



class PRelay(Relay):
	"""
	Extend :class:`Relay` with alternative implementation for :meth:`hasPlaceholder` and 
	:meth:`hasLock`.

	This class is useful if "placeheld" (respectively locked) files are available together 
	in a list.

	"P" stands for "page" and refers to the fact that placeholders and locks live as records.
	They may not be actual files.

	The :meth:`listPlaceheld` and :meth:`listLocked` methods should be overloaded.

	"""
	def listPlaceheld(self, remote_dir):
		"""
		List placeheld files.

		Arguments:

			remote_dir (str): path to a remote directory.

		Returns:

			list of str: list of paths to placeheld files.
		"""
		ls = self._list(remote_dir, recursive=False)
		return [ file for file in ls if self.isPlaceholder(file) ]

	def listLocked(self, remote_dir):
		"""
		List locked files.

		Arguments:

			remote_dir (str): path to a remote directory.

		Returns:

			list of str: list of paths to locked files.
		"""
		ls = self._list(remote_dir, recursive=False)
		return [ file for file in ls if self.isLock(file) ]

	def hasPlaceholder(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return filename in self.listPlaceheld(remote_dir)

	def hasLock(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return filename in self.listLocked(remote_dir)


