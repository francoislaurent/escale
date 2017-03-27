
from .relay import Relay
import easywebdav
import os
import itertools


class WebDAV(Relay):

	__protocol__ = ['webdav', 'https']

	def __init__(self, address, username=None, password=None, protocol=None, certificate=None, **ignored):
		Relay.__init__(self, address)
		self.username = username
		self.password = password
		self.protocol = protocol
		self.certificate = certificate

	def open(self):
		kwargs = {}
		if self.certificate:
			kwargs['protocol'] = 'https'
			kwargs['cert'] = self.certificate
		if self.protocol:
			kwargs['protocol'] = self.protocol
		try:
			self.address, kwargs['path'] = self.address.split('/', 1)
		except ValueError:
			pass
		self.webdav = easywebdav.connect(self.address, \
				username=self.username, password=self.password, \
				**kwargs)

	def diskFree(self):
		return None

	def hasLock(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		return self.webdav.exists(os.path.join(remote_dir, \
			'{}{}{}'.format(self._lock_prefix, filename, self._lock_suffix)))

	def _list(self, remote_dir, recursive=True, begin=None):
		try:
			ls = self.webdav.ls(remote_dir)
		except easywebdav.client.OperationFailed as e:
			if e.actual_code == 404:
				return []
			else:
				raise e
		if begin is None:
			if remote_dir[0] != '/':
				remote_dir = '/' + remote_dir
			if remote_dir[-1] != '/':
				remote_dir += '/'
			begin = len(remote_dir)
		files = [ file.name[begin:] for file in ls if file.contenttype ] # list names (not paths) of files (no directory)
		if recursive:
			files = list(itertools.chain(files, \
				*[ self._list(file.name, True, begin) for file in ls \
					if not file.contenttype \
						and len(remote_dir) < len(file.name) \
						and os.path.split(file.name[:-1])[1][0] != '.' ]))
		#print(('WebDAV._list: remote_dir, files', remote_dir, files))
		return files

	def push(self, local_file, remote_file):
		# webdav destination should be a path to file
		remote_dir, _ = os.path.split(remote_file)
		self.webdav.mkdirs(remote_dir)
		self.webdav.upload(local_file, remote_file)

	def pop(self, remote_file, local_file, unlink=True):
		# local destination should be a file
		#print(('WebDAV.pop: *args', remote_file, local_file, unlink))
		local_dir = os.path.dirname(local_file)
		if not os.path.isdir(local_dir):
			os.makedirs(local_dir)
		self.webdav.download(remote_file, local_file)
		if unlink:
			#print('deleting {}'.format(remote_file)) # debug
			self.webdav.delete(remote_file)

	def releaseLock(self, remote_file):
		remote_dir, filename = os.path.split(remote_file)
		self.webdav.delete(os.path.join(remote_dir, \
			'{}{}{}'.format(self._lock_prefix, filename, self._lock_suffix)))


