
from .relay import Relay
import easywebdav


class WebDAV(Relay):

	__protocol__ = ['webdav', 'https']

	def __init__(self, address, username=None, password=None, certificate=None, **ignored):
		self.address = address
		self.username = username
		self.password = password
		self.certificate = certificate

	def open(self):
		if self.certificate:
			self.webdav = easywebdav.connect(self.address, \
				username=self.username, password=self.password, \
				protocol='https', cert=self.certificate)
		else:
			self.webdav = easywebdav.connect(self.address, \
				username=self.username, password=self.password)

	def diskFree(self):
		return None

	def _list(self, webdav_dir):
		return self.webdav.ls(webdav_dir)

	def push(self, local_file, webdav_dest):
		# TODO: check that webdav_dest points to a file and not a directory
		webdav_file = webdav_dest
		self.webdav.upload(local_file, webdav_file)

	def pop(self, webdav_file, local_dest, unlink=True):
		# TODO: check whether local_dest should point to a file or can be a directory as well
		self.webdav.download(webdav_file, local_dest)
		if unlink:
			self.webdav.delete(webdav_file)


