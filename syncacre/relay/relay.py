
import os
import six
import time
import tempfile


def _special_push(self, remote_file, prefix, suffix, content=None):
	#print(('relay._special_push: remote_file', remote_file))
	remote_dir, filename = os.path.split(remote_file)
	if six.PY3:
		local_file = tempfile.mkstemp()
	elif six.PY2:
		_, local_file = tempfile.mkstemp()
	f = open(local_file, 'w')
	if content:
		f.write(content)
	f.close()
	self.push(local_file, os.path.join(remote_dir, '{}{}{}'.format(prefix, filename, suffix)))
	os.unlink(local_file)


def _special_unlink(self, remote_file, prefix, suffix):
	#print(('relay._special_unlink: remote_file', remote_file))
	remote_dir, filename = os.path.split(remote_file)
	if six.PY3:
		trash = tempfile.mkstemp()
	elif six.PY2:
		_, trash = tempfile.mkstemp()
	self.pop(os.path.join(remote_dir, '{}{}{}'.format(prefix, filename, suffix)), trash, True)
	os.unlink(trash)


def _special_filter(ls, prefix, suffix):
	if suffix:
		end = -len(suffix)
	else:
		end = None
	return [ os.path.join(filedir, filename[len(prefix):end]) \
		for filedir, filename in [ os.path.split(f) for f in ls ] \
		if filename.startswith(prefix) and filename.endswith(suffix) ]




class Relay(object):
	__slots__ = [ 'address', '_placeholder_prefix', '_placeholder_suffix', '_lock_prefix', '_lock_suffix' ]

	def __init__(self, address):
		self.address = address
		self._placeholder_prefix = '.'
		self._placeholder_suffix = '.placeholder'
		self._lock_prefix = '.'
		self._lock_suffix = '.lock'

	def open(self):
		pass

	def diskFree(self):
		raise NotImplementedError('abstract method')

	def listReady(self, remote_dir, recursive=True):
		ls = self._list(remote_dir, recursive=recursive)
		ready = []
		for file in ls:
			filedir, filename = os.path.split(file)
			if not (filename.startswith(self._lock_prefix) \
					and filename.endswith(self._lock_suffix)) \
				and not (filename.startswith(self._placeholder_prefix) \
					and filename.endswith(self._placeholder_suffix)) \
				and '{}{}{}'.format(self._lock_prefix, filename, self._lock_suffix) \
					not in ls:
				ready.append(file)
		return ready

	def listTransfered(self, remote_dir, end2end=True, recursive=True):
		ls = self._list(remote_dir, recursive=recursive)
		#print(('Relay.listTransfered: ls', ls))
		placeholders = _special_filter(ls, self._placeholder_prefix, self._placeholder_suffix)
		if end2end:
			return placeholders
		else:
			locks = _special_filter(ls, self._lock_prefix, self._lock_suffix)
			#print(('Relay.listTransfered: placeholders, locks', placeholders, locks))
			return placeholders + locks

	def listLocked(self, remote_dir, recursive=True):
		ls = self._list(remote_dir, recursive=recursive)
		return _special_filter(ls, self._lock_prefix, self._lock_suffix)

	def hasLock(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return filename in self.listLocked(remote_dir, recursive=False)

	def _list(self, remote_dir, recursive=True):
		raise NotImplementedError('abstract method')

	def acquireLock(self, remote_file, blocking=True):
		if blocking:
			if blocking is True:
				blocking = 60 # translate it to time, in seconds
			while self.hasLock(remote_file):
				print('sleeping {} seconds'.format(blocking))
				time.sleep(blocking)
		elif hasLock(self, remote_file):
			return
		_special_push(self, remote_file, self._lock_prefix, self._lock_suffix)

	def push(self, local_file, remote_dest):
		raise NotImplementedError('abstract method')

	def safePush(self, local_file, remote_dest, relative_path=None, placeholder=True):
		if not relative_path:
			_, relative_path = os.path.split(local_file)
		remote_dir = remote_dest # TODO: check this and adjust
		remote_file = os.path.join(remote_dir, relative_path)
		self.acquireLock(remote_file)
		if placeholder:
			# TODO: check whether placeholder is present
			#self.unlinkPlaceholder(remote_file)
			pass
		self.push(local_file, remote_file)
		self.releaseLock(remote_file)

	def pop(self, remote_file, local_dest, unlink=True, makedirs=True):
		raise NotImplementedError

	def safePop(self, remote_file, local_dest, unlink=True, placeholder=True):
		# TODO: ensure that local_dest is a path to a file and not a directory
		self.acquireLock(remote_file)
		self.pop(remote_file, local_dest, unlink)
		if placeholder:
			self.updatePlaceholder(remote_file)
		self.releaseLock(remote_file)

	def updatePlaceholder(self, remote_file, last_modified=None):
		_special_push(self, remote_file, self._placeholder_prefix, self._placeholder_suffix, \
			last_modified)

	def unlinkPlaceholder(self, remote_file):
		_special_unlink(self, remote_file, self._placeholder_prefix, self._placeholder_suffix)

	def releaseLock(self, remote_file):
		_special_unlink(self, remote_file, self._lock_prefix, self._lock_suffix)

	def close(self):
		pass


