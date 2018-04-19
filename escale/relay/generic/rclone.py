# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#      Contributor: François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale import *
from escale.base import *
from ..relay import Relay
from escale.base.subprocess import *
import os
import time



def rclone_binary(name=None):
	if name:
		_name = os.path.expanduser(name)
		if not os.path.isabs(_name): # and '/' in _name?
			_name = os.path.join(os.getcwd(), _name)
		if os.path.isfile(_name):
			return _name
	else:
		name = 'rclone'
	try:
		exec_path = os.environ['PATH'].split(':')
	except KeyError:
		try:
			# running arbitrary commands is not safe
			v = with_subprocess(name, 'version', output=True)
		except:
			pass
		else:
			if v.startswith('rclone '):
				# found
				return name
	else:
		for path in exec_path:
			_path = os.path.join(path, name)
			if os.path.isfile(_path):
				return _path
	return None


_supported_protocols = [ 'amazoncloud', 'b2', 'dropbox', 'googlecloud', 'hubic', 'onedrive', 'sftp', 'swift', 's3' ]


class RClone(Relay):
	"""
	Implements `Relay` for the various protocols supported by `rclone <https://rclone.org>`_.
	"""

	__protocol__ = ['rclone'] + _supported_protocols

	_is_multi_path = True

	def __init__(self, client, remote, repository, rclone_bin=None, config={}, **super_args):
		Relay.__init__(self, client, asstr(remote), asstr(repository), **super_args)
		if not rclone_bin:
			rclone_bin = config.get('rclone binary', None)
		rclone_bin = rclone_binary(rclone_bin)
		if not rclone_bin:
			raise ValueError("cannot find rclone executable file")
		self.rclone_bin = rclone_bin

	@property
	def remote(self):
		return self.address

	@remote.setter
	def remote(self, r):
		self.address = r

	def storageSpace(self):
		"""
		"""
		output = with_subprocess(self.rclone_bin, 'size', \
				'{}:{}'.format(self.remote, self.repository), error=IOError)
		used = None
		total = None
		_used_label = 'Total size:'
		#_total_label = ''
		for line in output.splitlines():
			if line.startswith(_used_label):
				used = float(line.split()[4][1:])
				if total is not None:
					break
			#elif line.startswith(_total_label):
			#	total = int(line[len(_total_label)+1:].split()[0])
			#	if used is not None:
			#		break
		used /= 1048576 # in MB
		return (used, total)

	def _list(self, remote_dir='', recursive=True, stats=[]):
		"""
		"""
		if remote_dir:
			relay_dir = os.path.join(self.repository, asstr(remote_dir))
		else:
			relay_dir = self.repository
		cmd = 'ls'
		if not recursive:
			raise NotImplementedError
		if stats:
			cmd = 'lsl'
		try:
			ls = with_subprocess(self.rclone_bin, cmd,
				'{}:{}'.format(self.remote, relay_dir),
				error=IOError) #'--fast-list', 
		except IOError as e:
			err = e.args[0].rstrip()
			if err.endswith('Unknown type *files.DeletedMetadata'):
				self.logger.debug(err)
				return []
			else:
				self.logger.error("unexpected rclone error for command %s on relay dir '%s': %s", cmd, relay_dir, err)
				raise
		if stats:
			files = []
			sizes = []
			mtimes = []
			for line in ls.splitlines():
				record = line.split(None, 3)
				size = record[0]
				path = record[3]
				mtime = record[1] + ' ' + record[2].split('.')[0]
				mtime = time.strptime(mtime, '%Y-%m-%d %H:%M:%S')
				files.append(path)
				sizes.append(size)
				mtimes.append(mtime)
			files = [ files ]
			for s in stats:
				if s == 'size':
					files.append(sizes)
				elif s == 'mtime':
					files.append(mtimes)
			return zip(*files)
		else:
			return [ line.split(None, 1)[2] for line in ls.splitlines() ]

	def exists(self, remote_file, dirname=None):
		remote_file = asstr(remote_file)
		if dirname:
			relay_file = os.path.join(self.repository, asstr(dirname), remote_file)
		else:
			relay_file = os.path.join(self.repository, remote_file)
		relay_file = '{}:{}'.format(self.remote, relay_file)
		while True:
			output = with_subprocess(self.rclone_bin, 'ls', relay_file, output=True)
			if isinstance(output, tuple):
				_, error = output
				error = error.rstrip().rstrip('.')
				if error.endswith('not found'):
					return False
				elif error.endswith('Unknown type *files.DeletedMetadata') or \
					error.endswith('Failed to ls: path/not_folder/'):
					self.logger.debug("rclone error on command 'ls': %s", error)
					continue # retry
				else:
					self.logger.debug("TODO: handle the following rclone output for relay file '%s': %s", relay_file, output)
					raise IOError(error)
			else:
				try:
					return not output or int(output.lstrip()[0])
				except IndexError:
					self.logger.debug("unexpected rclone output for relay file '%s': %s", relay_file, output)
					return False
			break

	def _push(self, local_file, remote_file, makedirs=True):
		"""
		`makedirs` is ignored (always True).
		"""
		relay_file = os.path.join(self.repository, asstr(remote_file))
		output = with_subprocess(self.rclone_bin, 'copyto', local_file,
				'{}:{}'.format(self.remote, relay_file),
				'--ignore-size', '--ignore-times',
				output=True)
		if isinstance(output, tuple):
			_, error = output
			error_count = 1
			for line in error.splitlines():
				if line.startswith('Errors:'):
					error_count = int(line.split()[-1])
					break
			if 0 < error_count:
				raise IOError(error)


	def _pop(self, remote_file, local_file, makedirs=True, _unlink=True):
		relay_file = os.path.join(self.repository, asstr(remote_file))
		if makedirs:
			dirname = os.path.dirname(local_file)
			if not os.path.isdir(dirname):
				os.makedirs(dirname)
		output = with_subprocess(self.rclone_bin, 'moveto' if _unlink else 'copyto',
				'{}:{}'.format(self.remote, relay_file), local_file,
				output=True)
		if isinstance(output, tuple):
			_, error = output
			if error.splitlines()[-1].startswith('Elapsed time:'):
				pass
			elif 'Failed to create file system for "' in error:
				raise MissingResource
			else:
				raise IOError(error)

	def unlink(self, remote_file):
		relay_file = '{}:{}'.format(self.remote, os.path.join(self.repository, asstr(remote_file)))
		output = with_subprocess(self.rclone_bin, 'delete', relay_file, output=True)
		if isinstance(output, tuple):
			#_, error = output
			pass

	def purge(self, remote_dir=''):
		relay_file = '{}:{}'.format(self.remote, os.path.join(self.repository, asstr(remote_file)))
		output = with_subprocess(self.rclone_bin, 'purge', relay_file, output=True)
		if isinstance(output, tuple):
			#_, error = output
			pass

