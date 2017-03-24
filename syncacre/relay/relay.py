
import os
import tempfile


def _special_push(self, remote_file, prefix, suffix, content=None):
	remote_dir, filename = os.path.split(remote_file)
	local_file = tempfile.mkstemp()
	f = open(local_file, 'w')
	if content:
		f.write(content)
	f.close()
	self.push(local_file, os.path.join(remote_dir, '{}{}{}'.format(prefix, filename, suffix)))
	try:
		os.unlink(local_file)
	except:
		pass


def _special_unlink(self, remote_file, prefix, suffix):
	remote_dir, filename = os.path.split(remote_file)
	trash = tempfile.mkstemp()
	try:
		self.pop(os.path.join(remote_dir, '{}{}{}'.format(prefix, filename, suffix)), trash)
	except:
		pass
	os.unlink(trash)



class Relay(object):
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

	def listReady(self, remote_dir):
		ls = self._list(remote_dir)
		return [ filename for filename in ls \
			if not (filename.startswith(lock_prefix) and filename.endswith(lock_suffix)) \
			and not (filename.startswith(placeholder_prefix) and filename.endswith(placeholder_suffix)) \
			and not (

	def listTransfered(self, remote_dir, end2end=True):
		ls = self._list(remote_dir)
		if end2end:
			if placeholder_suffix:
				end = -len(placeholder_suffix)
			else:
				end = None
			return [ filename[len(placeholder_prefix):end] \
				for filename in ls \
				if filename.startswith(placeholder_prefix) \
					and filename.endswith(placeholder_suffix) ]
		else:
			raise NotImplementedError

	def listLocked(self, remote_dir):
		ls = self._list(remote_dir)
		if lock_suffix:
			end = -len(lock_suffix)
		else:
			end = None
		return [ filename[len(lock_prefix):end] \
			for filename in ls \
			if filename.startswith(lock_prefix) \
				and filename.endswith(lock_suffix) ]

	def checkLocked(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return filename in self.listLocked(remote_dir)

	def _list(self, remote_dir):
		raise NotImplementedError('abstract method')

	def acquireLock(self, remote_file, blocking=True):
		if blocking:
			if blocking is True:
				blocking = 60 # translate it to time, in seconds
			while checkLock(self, remote_file):
				time.sleep(blocking)
		elif checkLock(self, remote_file):
			return
		_special_push(self, remote_file, lock_prefix, lock_suffix)

	def push(self, local_file, remote_dest):
		raise NotImplementedError('abstract method')

	def safePush(self, local_file, remote_dest, placeholder=True):
		_, filename = os.path.split(local_file)
		remote_dir = remote_dest # TODO: check and adjust
		remote_file = os.path.join(remote_dir, filename)
		self.acquireLock(remote_file)
		if placeholder:
			# TODO: check whether placeholder is present
			#self.unlinkPlaceholder(remote_file)
			pass
		self.push(local_file, remote_file)
		self.releaseLock(remote_file)

	def pop(self, remote_file, local_dest, unlink=True):
		raise NotImplementedError

	def safePop(self, remote_file, local_dest, unlink=True, placeholder=True):
		self.acquireLock(remote_file)
		self.pop(remote_file, local_dest, unlink)
		if placeholder:
			self.updatePlaceholder(remote_file)
		self.releaseLock(remote_file)

	def updatePlaceholder(self, remote_file, last_modified=None):
		_special_push(self, remote_file, placeholder_prefix, placeholder_suffix, last_modified)

	def unlinkPlaceholder(self, remote_file):
		_special_unlink(self, remote_file, placeholder_prefix, placeholder_suffix)

	def releaseLock(self, remote_file):
		_special_unlink(self, remote_file, lock_prefix, lock_suffix)

	def close(self):
		pass


