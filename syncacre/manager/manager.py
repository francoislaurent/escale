
from __future__ import print_function

import time
import os
import sys
import itertools
from syncacre.encryption import Plain


class Manager(object):

	def __init__(self, relay, path=None, address=None, directory=None, mode=None, \
		encryption=Plain(None), \
		refresh=None, verbose=True, **relay_args):
		if path[-1] != '/':
			path += '/'
		self.path = path
		self.dir = directory
		self.mode = mode
		self.encryption = encryption
		self.refresh = refresh
		self.verbose = verbose
		self.relay = relay(address, **relay_args)

	def run(self):
		self.logBegin('connecting with {}', self.relay.address)
		self.relay.open()
		self.logEnd()
		try:
			while True:
				if self.mode is None or self.mode == 'download':
					self.download()
				if self.mode is None or self.mode == 'upload':
					self.upload()
				if self.refresh:
					self.logBegin('sleeping {} seconds', self.refresh)
					time.sleep(self.refresh)
					self.logEnd()
				else:
					break
		except KeyboardInterrupt:
			pass
		self.relay.close()

	def download(self):
		remote = self.relay.listReady(self.dir)
		#print(('Manager.run/download: remote', remote))
		for filename in remote:
			local_file = os.path.join(self.path, filename)
			remote_file = os.path.join(self.dir, filename)
			if os.path.isfile(local_file):
				# TODO: check last modified information
				#continue
				if self.verbose:
					print('file {} already exists; overwriting'.format(filename))
			temp_file = self.encryption.prepare(local_file)
			self.logBegin('downloading file {}', filename)
			self.relay.safePop(remote_file, temp_file)
			self.logEnd()
			self.encryption.decrypt(temp_file, local_file)
			

	def upload(self):
		local = self.localFiles()
		remote = self.relay.listTransfered(self.dir, end2end=False)
		#print(('Manager.upload: local, remote', local, remote))
		for local_file in local:
			filename = local_file[len(self.path):] # relative path
			if filename not in remote:
				# TODO: check disk usage on relay
				temp_file = self.encryption.encrypt(local_file)
				self.logBegin('uploading file {}', filename)
				self.relay.safePush(temp_file, self.dir, \
					relative_path=filename)
				self.logEnd()
				self.encryption.finalize(temp_file)

	def logBegin(self, msg, *args):
		if self.verbose:
			print((msg + '... ').format(*args), end='')
			sys.stdout.flush()

	def logEnd(self):
		if self.verbose:
			print('[done]')

	def localFiles(self, path=None):
		if path is None:
			path = self.path
		ls = [ os.path.join(path, file) for file in os.listdir(path) if file[0] != '.' ]
		local = itertools.chain([ file for file in ls if os.path.isfile(file) ], \
			*[ self.localFiles(file) for file in ls if os.path.isdir(file) ])
		return list(local)


