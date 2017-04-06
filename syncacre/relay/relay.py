
import os
import sys
import time
import tempfile



def _get_temp_file():
	_, name = tempfile.mkstemp()
	return name


def _special_filter(ls, prefix, suffix):
	if suffix:
		end = -len(suffix)
	else:
		end = None
	return [ os.path.join(filedir, filename[len(prefix):end]) \
		for filedir, filename in [ os.path.split(f) for f in ls ] \
		if filename.startswith(prefix) and filename.endswith(suffix) ]


def with_path(path, fun, *args, **kwargs):
	_dir, _file = os.path.split(path)
	return os.path.join(_dir, fun(_file, *args, **kwargs))



class Relay(object):
	__slots__ = [ 'address', '_placeholder_prefix', '_placeholder_suffix', '_lock_prefix', '_lock_suffix' ]

	def __init__(self, address):
		self.address = address
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

	def diskFree(self):
		raise NotImplementedError('abstract method')

	def _list(self, remote_dir, recursive=True):
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
		raise NotImplementedError('abstract method')

	def hasLock(self, remote_file):
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

		To pop or get a file, use meth:`markAsRead` instead.
		"""
		self.touch(self.placeholder(remote_file), last_modified)

	def acquireLock(self, remote_file, blocking=True):
		if blocking:
			if blocking is True: # if not numerical
				blocking = 60 # translate it to time, in seconds
			while self.hasLock(remote_file):
				print('sleeping {} seconds'.format(blocking))
				time.sleep(blocking)
		elif self.hasLock(remote_file):
			return False
		self.touch(self.lock(remote_file))
		return True

	def releaseLock(self, remote_file):
		self.unlink(self.lock(remote_file))

	def _push(self, local_file, remote_dest):
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
		self._get(remote_file, local_dest, makedirs)
		self.unlink(remote_file)

	def _get(self, remote_file, local_dest, makedirs=True):
		#raise NotImplementedError
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

	def close(self):
		pass




class IRelay(Relay):

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


