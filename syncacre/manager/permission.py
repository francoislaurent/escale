# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from syncacre.base.essential import *
import os
import itertools


if PYTHON_VERSION == 2:
	class PermissionError(EnvironmentError):
		pass


class Accessor(object):
	"""
	Interface to a single local file.

	This class aims at hiding the actual file so that access to it is 
	strictly controlled, while still featuring basic file manipulation 
	methods.
	"""
	__slots__ = ['exists', 'delete']
	def __init__(self, exists=None, delete=None):
		self.exists = exists
		self.delete = delete


class PermissionController(Reporter):
	"""
	Manage access to the files in a local repository.

	This class is an experimental feature that prepares the introduction
	of access permission for individual files as expected in the future
	``0.5`` release.

	Attributes:

		repository (str): repository identifier.

		path (str): path to repository root.

		mode (None or str): either ``'download'`` or ``'upload'`` or ``None`` 
			(both download and upload).
	"""
	def __init__(self, repository, path=None,
			ui_controller=None,
			push_only=False, pull_only=False,
			**args):
		Reporter.__init__(self, ui_controller=ui_controller)
		if not path:
			msg = 'no local repository defined'
			self.logger.error(msg)
			raise KeyError(msg)
		if path[-1] != '/':
			path += '/'
		self.path = path
		# set operating mode
		self.mode = None
		if push_only:
			if pull_only:
				msg = 'both read only and write only; cannot determine mode'
				self.logger.error(msg)
				raise KeyError(msg)
			else:
				self.mode = 'upload'
		elif pull_only:
			self.mode = 'download'

	def readableFiles(self, path=None):
		"""
		List all visible files in the local repository.

		Files which name begins with "." are ignored.
		"""
		if path is None:
			path = self.path
		ls = [ os.path.join(path, f) for f in os.listdir(path) if f[0] != '.' ]
		local = itertools.chain([ f for f in ls if os.path.isfile(f) ], \
			*[ self.localFiles(f) for f in ls if os.path.isdir(f) ])
		return list(local)

	def writable(self, filename):
		if self.mode == 'upload':
			return None
		else:
			return join(self.path, filename)

	def accessor(self, filename):
		local_file = join(self.path, filename)
		if os.path.isfile(local_file):
			def exists():
				return True
			if self.mode == 'download':
				def delete():
					os.unlink(local_file)
			else:
				def delete():
					raise PermissionError(local_file)
		else:
			def exists():
				return False
			def delete():
				pass
		return Accessor(exists=exists, delete=delete)

