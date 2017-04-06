
from .relay import Relay
import easywebdav
import requests
import os
import sys
import itertools


class WebDAVClient(easywebdav.Client):
	def __init__(self, host, max_retry=1, retry_after=60, verbose=False, url='', **kwargs):
		easywebdav.Client.__init__(self, host, **kwargs)
		self.max_retry = max_retry
		self.retry_after = retry_after
		self.verbose = verbose
		self.url = url # for debug purposes

	def _send(self, *args, **kwargs):
		try:
			if self.max_retry is None:
				return easywebdav.Client._send(self, *args, **kwargs)
			else:
				count = 0
				while count <= self.max_retry:
					try:
						return easywebdav.Client._send(self, *args, **kwargs)
					except requests.exceptions.ConnectionError as e:
						count += 1
						if count <= self.max_retry:
							if self.verbose:
								print('warning: connection error')
								print('         {}'.format(e.args))
							time.sleep(self.retry_after)
				if self.verbose:
					print('warning: too many connection attempts.')
				raise e
		except easywebdav.OperationFailed as e:
			if e.actual_code == 403:
				path = args[1]
				print("access to '{}{}' forbidden".format(self.url, path))
			raise e


class WebDAV(Relay):

	__protocol__ = ['webdav', 'https']

	def __init__(self, address, username=None, password=None, protocol=None, certificate=None, \
		max_retry=True, retry_after=None, **ignored):
		Relay.__init__(self, address)
		if sys.version_info[0] == 3: # deal with encoding issues with requests
			username = username.encode('utf-8').decode('unicode-escape')
			password = password.encode('utf-8').decode('unicode-escape')
		self.username = username
		self.password = password
		self.protocol = protocol
		self.certificate = certificate
		self.max_retry = max_retry
		self.retry_after = retry_after

	def open(self):
		kwargs = {}
		if self.certificate:
			kwargs['protocol'] = 'https'
			kwargs['cert'] = self.certificate
		if self.protocol:
			kwargs['protocol'] = self.protocol
		try:
			self.address, self.path = self.address.split('/', 1)
			kwargs['path'] = self.path
		except ValueError:
			pass
		if self.max_retry is not True: # WebDAVClient has max_retry set; trust default value there
			kwargs['max_retry'] = self.max_retry
		if self.retry_after is not None:
			kwargs['retry_after'] = self.retry_after
		# url is for debug purposes
		try:
			url = '{}://{}/{}/'.format(self.protocol, self.address, self.path)
		except:
			try:
				url = '{}://{}/'.format(self.protocol, self.address)
			except:
				pass
		# establish connection (session)
		self.webdav = WebDAVClient(self.address, verbose=True, url=url, \
				username=self.username, password=self.password, \
				**kwargs)
		#self.webdav.session.headers['Charset'] = 'utf-8' # for Python 3

	def diskFree(self):
		return None

	def hasPlaceholder(self, remote_file):
		return self.webdav.exists(self.placeholder(remote_file))

	def hasLock(self, remote_file):
		return self.webdav.exists(self.lock(remote_file))

	def _list(self, remote_dir, recursive=True, begin=None):
		if not remote_dir:
			remote_dir = '.' # easywebdav default
		try:
			ls = self.webdav.ls(remote_dir)
		except easywebdav.OperationFailed as e:
			if e.actual_code == 404:
				return []
			else:
				if e.actual_code != 403:
					print("easywebdav.Client.ls('{}') failed".format(remote_dir))
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

	def _push(self, local_file, remote_file, makedirs=True):
		# webdav destination should be a path to file
		if makedirs:
			remote_dir, _ = os.path.split(remote_file)
			self.webdav.mkdirs(remote_dir)
		self.webdav.upload(local_file, remote_file)

	def _get(self, remote_file, local_file, makedirs=True):
		# local destination should be a file
		#print(('WebDAV._get: *args', remote_file, local_file, unlink))
		local_dir = os.path.dirname(local_file)
		if makedirs and not os.path.isdir(local_dir):
			os.makedirs(local_dir)
		self.webdav.download(remote_file, local_file)

	def unlink(self, remote_file):
		#print('deleting {}'.format(remote_file)) # debug
		self.webdav.delete(remote_file)


