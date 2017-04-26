# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

import os
import sys
import time
import tempfile

from syncacre.log import log_root


def _get_temp_file():
	_, name = tempfile.mkstemp()
	return name


def with_path(path, fun, *args, **kwargs):
	"""
	Helper function that applies a string manipulation function to the filename part of a path.
	"""
	_dir, _file = os.path.split(path)
	return os.path.join(_dir, fun(_file, *args, **kwargs))



class AbstractRelay(object):
	"""
	Sends files to/from a remote host.

	This class is an interface that groups together the methods called by 
	:class:`syncacre.manager.Manager`.

	Attributes:

		address (str): address of the remote host.

		logger (Logger or LoggerAdapter): repository-related logger.

	"""
	__slots__ = ['address', 'logger']

	def __init__(self, address, logger=None):
		self.address = address
		self.logger = logger

	def open(self):
		"""
		Establishes the connection with the remote host.

		Returns:

			bool: True if successful, False if failed.
		"""
		raise NotImplementedError('abstract method')

	def diskFree(self):
		"""
		Queries for how much space is available on the remote host.

		Returns:

			int or float: available space in kilobytes.
		"""
		raise NotImplementedError('abstract method')

	def listReady(self, remote_dir, recursive=True):
		"""
		Gets the files on the remote host that are ready for download.

		Arguments:

			remote_dir (str): remote directory to "ls".

			recursive (bool): whether to list subdirectories or not.

		Returns:

			list of str: list of relative paths.
		"""
		raise NotImplementedError('abstract method')

	def listTransfered(self, remote_dir, end2end=True, recursive=True):
		"""
		Gets the files on the remote host that were transfered.

		Arguments:

			remote_dir (str): relative path to remote directory to "ls".

			end2end (bool): if True, list only files that are no longer
				available on the remote host.

			recursive (bool): whether to list subdirectories or not.

		Returns:

			list of str: list of relative paths.
		"""
		raise NotImplementedError('abstract method')

	def getPlaceholder(self, remote_file):
		"""
		Downloads the placeholder file.

		It makes a temporary file to be manually unlinked once done with it.

		Example:

		.. code-block:: python

			import os

			placeholder = relay.getPlaceholder(path_to_remote_file)

			with open(placeholder, 'r') as f:
				# do something with `f`

			os.unlink(placeholder)

		
		Arguments:

			remote_file (str): relative path to regular file (not placeholder or lock).

		Returns:

			str: path to local copy of the placeholder file.
		"""
		raise NotImplementedError('abstract method')

	def push(self, local_file, remote_dest, relative_path=None, last_modified=None, blocking=True):
		"""
		Uploads a file to the remote host.

		Arguments:

			local_file (str): path to the local file to be sent.

			remote_dest (str): path to the target directory on the remote host.

			relative_path (str): target relative path or filename, if to be different
				from filename in `local_file`.

			last_modified (str): meta information to be recorded for the remote copy.

			blocking (bool): if target exists and is locked, whether should we block 
				until the lock is released or skip the file.

		Returns:

			bool: True if successful, False if failed.
		"""
		raise NotImplementedError('abstract method')

	def pop(self, remote_file, local_dest, blocking=True, placeholder=1, **kwargs):
		"""
		Downloads a file from the remote host and unlinks remote copy if relevant.

		Arguments:

			remote_file (str): relative path to the remote file.

			local_dest (str): path to the target local file.

			blocking (bool): if target exists and is locked, whether should we block 
				until the lock is released or skip the file.

			placeholder (bool or int): whether to generate a placeholder file.
				If an int is given, it gives the number of downloading clients
				(usually the total number of clients minus one).

		Returns:

			bool: True if successful, False if failed.
		"""
		raise NotImplementedError('abstract method')

	def close(self):
		"""
		Closes the connection with the remote host.

		Returns:

			bool: True if successful, False if failed.
		"""
		raise NotImplementedError('abstract method')


class Relay(AbstractRelay):
	"""
	Sends files to/from a remote relay.

	This class is a partial implementation of :class:`AbstractRelay`.
	Especially, it implements independent placeholders and locks.

	Placeholders and locks are named after the corresponding regular files.
	Extra strings are prepended and appended to the regular filename.

	Any derivative class should implement:

	* :meth:`_list`
	* :meth:`hasPlaceholder` and :meth:`hasLock`
	* :meth:`_push` and either:

		* :meth:`_get`
		* :meth:`_pop` with `_unlink` optional argument
		* both :meth:`_get` and :meth:`_pop`

	Attributes:

		_placeholder_prefix (str): prefix for placeholder files.

		_placeholder_suffix (str): suffix for placeholder files.

		_lock_prefix (str): prefix for lock files.

		_lock_suffix (str): suffix for lock files.

	"""
	__slots__ = AbstractRelay.__slots__ + \
		[ '_placeholder_prefix', '_placeholder_suffix', '_lock_prefix', '_lock_suffix' ]

	def __init__(self, address, logger=None):
		if logger is None:
			logger = logging.getLogger(log_root).getChild(address)
		AbstractRelay.__init__(self, address, logger=logger)
		self._placeholder_prefix = '.'
		self._placeholder_suffix = '.placeholder'
		self._lock_prefix = '.'
		self._lock_suffix = '.lock'

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

	def placeholder(self, path):
		return with_path(path, self._placeholder)

	def lock(self, path):
		return with_path(path, self._lock)

	def isPlaceholder(self, path):
		_, filename = os.path.split(path)
		return self._isPlaceholder(filename)

	def isLock(self, path):
		_, filename = os.path.split(path)
		return self._isLock(filename)

	def fromPlaceholder(self, path):
		return with_path(path, self._fromPlaceholder)

	def fromLock(self, path):
		return with_path(path, self._fromLock)


	def open(self):
		pass

	def close(self):
		pass

	def _list(self, remote_dir, recursive=True):
		"""
		List all files, including hidden files, relative to `remote_dir`.

		Arguments:

			remote_dir (str): directory on the remote host.

			recursive (bool): if ``True``, list files in subdirectories as well.

		Returns:

			list of str: list of relative paths.

		"""
		raise NotImplementedError('abstract method')

	def listReady(self, remote_dir, recursive=True):
		ls = self._list(remote_dir, recursive=recursive)
		ready = []
		for file in ls:
			filedir, filename = os.path.split(file)
			if not self._isLock(filename) and not self._isPlaceholder(filename) \
				and os.path.join(filedir, self._lock(filename)) not in ls:
				ready.append(file)
		return ready

	def listTransfered(self, remote_dir, end2end=True, recursive=True):
		ls = self._list(remote_dir, recursive=recursive)
		#print(('Relay.listTransfered: ls', ls))
		placeholders = []
		others = []
		for file in ls:
			if self.isPlaceholder(file):
				placeholders.append(self.fromPlaceholder(file))
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
				else:
					others.append(file)
			#print(('Relay.listTransfered: placeholders, locks', placeholders, locks))
			return others + placeholders + locks

	def touch(self, remote_file, content=None):
		#print(('relay.touch: remote_file content', remote_file, content))
		local_file = _get_temp_file()
		f = open(local_file, 'w')
		if content:
			f.write(content)
		f.close()
		self._push(local_file, remote_file)
		os.unlink(local_file)

	def unlink(self, remote_file):
		trash = _get_temp_file()
		self._pop(remote_file, trash)
		os.unlink(trash)

	def hasPlaceholder(self, remote_file):
		"""
		Checks for placeholder presence.

		Arguments:

			remote_file (str): relative path to a regular file on the remote host.

		Returns:

			bool: ``True`` if there exists a placeholder for `remote_file`, 
				``False`` otherwise.

		"""
		raise NotImplementedError('abstract method')

	def hasLock(self, remote_file):
		"""
		Checks for lock presence.

		Arguments:

			remote_file (str): relative path to a regular file on the remote host.

		Returns:

			bool: ``True`` if there exists a lock for `remote_file`, 
				``False`` otherwise.

		"""
		raise NotImplementedError('abstract method')

	def getPlaceholder(self, remote_file):
		if self.hasPlaceholder(remote_file):
			remote_placeholder = self.placeholder(remote_file)
			local_placeholder = _get_temp_file()
			self._get(remote_placeholder, local_placeholder)
			return local_placeholder
		else:
			return None

	def updatePlaceholder(self, remote_file, last_modified=None):
		"""
		Update a placeholder when the corresponding file is pushed.

		To pop or get a file, use :meth:`markAsRead` instead.
		"""
		self.touch(self.placeholder(remote_file), last_modified)

	def acquireLock(self, remote_file, blocking=True):
		if blocking:
			if blocking is True: # if not numerical
				blocking = 60 # translate it to time, in seconds
			while self.hasLock(remote_file):
				self.logger.debug('lock not available; waiting %s seconds', blocking)
				time.sleep(blocking)
		elif self.hasLock(remote_file):
			return False
		self.touch(self.lock(remote_file))
		return True

	def releaseLock(self, remote_file):
		self.unlink(self.lock(remote_file))

	def _push(self, local_file, remote_dest):
		"""
		Sends a local file to the remote host.

		Arguments:

			local_file (str): path to a local file.

			remote_dest (str): path to a directory on the remote host.

		Returns:

			bool or nothing: ``True`` if transfer was successful, ``False`` otherwise.

		"""
		raise NotImplementedError('abstract method')

	def push(self, local_file, remote_dest, relative_path=None, last_modified=None, blocking=True):
		if not relative_path:
			_, relative_path = os.path.split(local_file)
		remote_dir = remote_dest # TODO: check this and adjust
		remote_file = os.path.join(remote_dir, relative_path)
		if not self.acquireLock(remote_file, blocking=blocking):
			return False
		if last_modified:
			self.updatePlaceholder(remote_file, last_modified=last_modified)
		self._push(local_file, remote_file)
		self.releaseLock(remote_file)
		return True

	def _pop(self, remote_file, local_dest, makedirs=True):
		"""
		Downloads a file and deletes it from the remote host.

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
		Downloads a file and does NOT delete it from the remote host.

		Arguments:

			remote_file (str): path to a file on the remote host.

			local_dest (str): path to a local directory.

			makedirs (bool): make directories if missing.

		Returns:

			bool or nothing: ``True`` if transfer was successful, ``False`` otherwise.

		"""
		self._pop(remote_file, local_dest, makedirs=makedirs, _unlink=False)

	def pop(self, remote_file, local_dest, blocking=True, placeholder=1, **kwargs):
		# TODO: ensure that local_dest is a path to a file and not a directory
		if not self.acquireLock(remote_file, blocking=blocking):
			return False
		let = False
		if placeholder:
			has_placeholder = self.hasPlaceholder(remote_file)
			if has_placeholder and 1 < placeholder:
				remote_placeholder = self.placeholder(remote_file)
				local_placeholder = _get_temp_file()
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
			else:
				self.updatePlaceholder(remote_file)
		self.releaseLock(remote_file)
		return True

	def get(self, remote_file, local_dest, blocking=True, placeholder=True, **kwargs):
		# TODO: ensure that local_dest is a path to a file and not a directory
		if not self.acquireLock(remote_file, blocking=blocking):
			return False
		self._get(remote_file, local_dest)
		if placeholder and self.hasPlaceholder(remote_file):
			self.markAsRead(remote_file, **kwargs)
		self.releaseLock(remote_file)
		return True

	def markAsRead(self, remote_file, client_name='', local_placeholder=None):
		remote_placeholder = self.placeholder(remote_file)
		if not local_placeholder:
			local_placeholder = _get_temp_file()
			self._get(remote_placeholder, local_placeholder)
		with open(local_placeholder, 'a') as f:
			f.write('\n{}'.format(client_name))
		self._push(local_placeholder, remote_placeholder)
		os.unlink(local_placeholder)




class IRelay(Relay):
	"""
	Extends :class:`Relay` with default implementation for :meth:`hasPlaceholder` and 
	:meth:`hasLock`.

	This class is not used at the moment.
	"""
	def listPlaceholders(self, remote_dir):
		ls = self._list(remote_dir, recursive=False)
		return [ file for file in ls if self.isPlaceholder(file) ]

	def listLocks(self, remote_dir):
		ls = self._list(remote_dir, recursive=False)
		return [ file for file in ls if self.isLock(file) ]

	def hasPlaceholder(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return self._placeholder(filename) in self.listPlaceholders(remote_dir)

	def hasLock(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return self._lock(filename) in self.listLocks(remote_dir)



class PDRelay(Relay):
	"""
	Extends :class:`Relay` with default implementation for :meth:`hasPlaceholder` and 
	:meth:`hasLock`.

	This class is not used at the moment.
	"""
	def listPlaceheld(self, remote_dir):
		ls = self._list(remote_dir, recursive=False)
		return [ file for file in ls if self.isPlaceholder(file) ]

	def listLocked(self, remote_dir):
		ls = self._list(remote_dir, recursive=False)
		return [ file for file in ls if self.isLock(file) ]

	def hasPlaceholder(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return filename in self.listPlaceheld(remote_dir)

	def hasLock(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return filename in self.listLocked(remote_dir)


