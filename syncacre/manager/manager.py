
import time
import calendar
import os
import sys
import itertools
from syncacre.encryption import Plain
from math import *


class Manager(object):
	"""
	Makes the glue between the local file system and the :mod:`~syncacre.relay` layer and 
	:mod:`~syncacre.encryption` layers.

	This class manages the meta information, file modifications and sleep times.

	Attributes:

		path (str): path to the local repository.

		dir (str): relative path to the repository on the remote host.

		mode (None or str): either 'download' or 'upload' or None (both download and upload).

		encryption (syncacre.encryption.Cipher): encryption layer.

		relay (syncacre.relay.AbstractRelay): communication layer.

		timestamp (bool or str): if True (recommended), manages file modification times. 
			If str, in addition determines the timestamp format as supported by 
			`time.strftime`.

		refresh (int): refresh interval in seconds.

		logger (Logger or LoggerAdapter): see the :mod:`logging` standard module.

		pop_args (dict): extra keyword arguments for :meth:`syncacre.AbstractRelay.pop`.
			Supported keyword arguments are:
			``client_name`` (`str`): name identifying the running client.

	"""
	def __init__(self, relay, address=None, path=None, directory=None, mode=None, \
		encryption=Plain(None), timestamp=True, refresh=None, logger=None, clientname=None, \
		**relay_args):
		self.logger = logger
		if path[-1] != '/':
			path += '/'
		self.path = path
		self.dir = directory
		self.mode = mode
		self.encryption = encryption
		if timestamp is True:
			timestamp = '%y%m%d_%H%M%S'
		self.timestamp = timestamp
		self.refresh = refresh
		self.pop_args = {}
		if clientname:
			self.pop_args['client_name'] = clientname
		self.relay = relay(address, logger=self.logger, **relay_args)

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
		self.logger.debug("connecting with '%s'", self.relay.address)
		ok = self.relay.open()
		if ok:
			self.logger.debug('connected')
		elif ok is not None:
			self.logger.critical("failed to connect with '%s'", self.relay.address)
		try:
			while True:
				if self.mode is None or self.mode == 'download':
					self.download()
				if self.mode is None or self.mode == 'upload':
					self.upload()
				if self.refresh:
					self.logger.debug('sleeping %s seconds', self.refresh)
					time.sleep(self.refresh)
				else:
					break
		except KeyboardInterrupt:
			pass
		self.relay.close()

	def download(self):
		"""
		Finds out which files are to be downloaded and download them.
		"""
		remote = self.relay.listReady(self.dir)
		#print(('Manager.download: remote', remote))
		for filename in remote:
			local_file = os.path.join(self.path, filename)
			remote_file = os.path.join(self.dir, filename)
			last_modified = None
			if self.timestamp:
				placeholder = self.relay.getPlaceholder(remote_file)
				if placeholder:
					with open(placeholder, 'r') as f:
						last_modified = f.readline().rstrip()
					os.unlink(placeholder)
					last_modified = time.strptime(last_modified, self.timestamp)
					last_modified = calendar.timegm(last_modified) # remote_mtime
			if os.path.isfile(local_file):
				if last_modified and last_modified <= floor(os.path.getmtime(local_file)):
					# local_mtime = os.path.getmtime(local_file)
					continue
				msg = "updating local file '%s'"
			else:
				msg = "downloading file '%s'"
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

	def upload(self):
		"""
		Finds out which files are to be uploaded and upload them.
		"""
		local = self.localFiles()
		remote = self.relay.listTransfered(self.dir, end2end=False)
		#print(('Manager.upload: local, remote', local, remote))
		for local_file in local:
			filename = local_file[len(self.path):] # relative path
			modified = False # if no remote copy, this is ignored
			if self.timestamp: # check file last modification time
				local_mtime = floor(os.path.getmtime(local_file))
				last_modified = time.gmtime(local_mtime) # UTC
				last_modified = time.strftime(self.timestamp, last_modified)
				if filename in remote:
					remote_file = os.path.join(self.dir, filename)
					placeholder = self.relay.getPlaceholder(remote_file)
					if placeholder:
						with open(placeholder, 'r') as f:
							remote_mtime = f.readline().rstrip()
						os.unlink(placeholder)
						remote_mtime = time.strptime(remote_mtime, self.timestamp)
						remote_mtime = calendar.timegm(remote_mtime)
						modified = remote_mtime < local_mtime
					#else: (TODO) directly read mtime on remote copy?
			else:
				last_modified = None
			if filename not in remote or modified:
				# TODO: check disk usage on relay
				temp_file = self.encryption.encrypt(local_file)
				self.logger.info("uploading file '%s'", filename)
				ok = self.relay.push(temp_file, self.dir, \
					relative_path=filename, blocking=False, \
					last_modified=last_modified)
				if ok:
					self.logger.debug("file '%s' successfully uploaded", filename)
				elif ok is not None:
					self.logger.warning("failed to upload '%s'", filename)
				self.encryption.finalize(temp_file) # delete encrypted copy

	def localFiles(self, path=None):
		"""
		Lists all files in the local repository.

		Files which name begins with "." are ignored.
		"""
		if path is None:
			path = self.path
		ls = [ os.path.join(path, file) for file in os.listdir(path) if file[0] != '.' ]
		local = itertools.chain([ file for file in ls if os.path.isfile(file) ], \
			*[ self.localFiles(file) for file in ls if os.path.isdir(file) ])
		return list(local)


