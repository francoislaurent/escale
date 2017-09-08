# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.essential import *
from .relay import Relay
import os
import time
import itertools


class LocalMount(Relay):
	"""
	Add support for local file system (mounts).
	"""

	__protocol__ = ['file']

	def __init__(self, client, address, mount_point, **super_args):
		if address and os.path.isabs(address):
			if not os.path.isdir(address):
				raise ValueError("relay mount path '{}' does not exist".format(address))
			mount_point = join(address, mount_point)
			address = 'localhost'
		Relay.__init__(self, client, address, mount_point, **super_args)

	def open(self):
		pass

	def storageSpace(self):
		used = 0
		files = self._list(recursive=True, stats=['size'])
		if files:
			files, sizes = zip(*files)
			used = float(sum(sizes)) / 1048576 # in MB
		return (used, None)

	def _list(self, relay_dir='', recursive=True, stats=[]):
		_listdir = not stats
		if relay_dir:
			dirname = os.path.join(self.repository, relay_dir)
		else:
			dirname = self.repository
		if stats:
			files = []
			dirs = []
			try:
				with os.scandir(dirname) as ls:
					for f in ls:
						if f.is_file():
							# os.DirEntry caches the result of stat()
							print(f.name)
							files.append((
								os.path.relpath(asstr(f.path), self.repository),
								f.stat().st_size,
								f.stat().st_mtime,
								))
						elif recursive and f.is_dir(): # '.' and '..' are excluded by os.scandir
							dirs.append(f.path)
			except AttributeError: # Python < 3.6
				_listdir = True
			else:
				if dirs:
					files = itertools.chain(files, *[self._list(d, stats=True) for d in dirs])
		if _listdir:
			ls = [ (os.path.join(relay_dir, f), os.path.join(dirname, f))
					for f in os.listdir(dirname) ]
			files = [ _rel for _rel, _abs in ls if os.path.isfile(_abs) ]
			if recursive:
				files = itertools.chain(files,
					*[ self._list(_rel) for _rel, _abs in ls if os.path.isdir(_abs) ])
			if stats: # Python < 3.6
				_files = []
				for f in files:
					s = os.stat(os.path.join(self.repository, f))
					_files.append((f, s.st_size, s.st_mtime))
				files = _files
		if files and stats and not isinstance(stats, bool):
			_files = {}
			_files['name'], _files['size'], _files['mtime'] = zip(*files)
			files = zip(*[ _files[i] for i in ['name']+list(stats) ])
		return files

	def exists(self, relay_file, dirname=None):
		path = [ self.repository ]
		if dirname:
			path.append(dirname)
		path.append(relay_file)
		return os.path.exists(os.path.join(*path))

	def _push(self, local_file, relay_dest, makedirs=True):
		dirname, basename = os.path.split(relay_dest)
		dest = os.path.join(self.repository, dirname)
		if makedirs and not os.path.isdir(dest):
			os.makedirs(dest)
		dest = os.path.join(dest, basename)
		copyfile(local_file, dest)

	def _get(self, relay_file, local_file, makedirs=True):
		src = os.path.join(self.repository, relay_file)
		if makedirs:
			dirname = os.path.dirname(local_file)
			if not os.path.isdir(dirname):
				os.makedirs(dirname)
		copyfile(src, local_file)

	def unlink(self, relay_file):
		os.unlink(os.path.join(self.repository, relay_file))

#	def listTransfered(self, remote_dir, end2end=True, recursive=True):
#		# Manager.run has completed Manager.download and is initiating Manager.upload
#		if self.after_pull_delay:
#			# caching on local mount may delay the addition of new files
#			time.sleep(self.after_pull_delay)
#		return Relay.listTransfered(self, remote_dir, end2end=end2end, recursive=recursive)

	def purge(self, relay_dir=''):
		import shutil
		shutil.rmtree(os.path.join(self.repository, relay_dir))

