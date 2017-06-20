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


drive_exec = [ 'drive-google', 'drive' ]
default_mount_point = os.path.join(os.path.expanduser('~'), '.config', PROGRAM_NAME, '.GoogleDrive')


def drive_binary(name=None):
	if name:
		name = os.path.expanduser(name)
		if os.path.isabs(name) and os.path.isfile(name):
			# nothing to do
			return name
		exec_names = [ name ]
	else:
		exec_names = drive_exec
	try:
		exec_path = os.environ['PATH'].split(':')
	except KeyError:
		for _name in exec_names:
			try:
				# running arbitrary commands is not safe
				v = with_subprocess(_name, 'version', output=True)
			except:
				pass
			else:
				if v.startswith('drive '):
					# found
					return _name
	else:
		for path in exec_path:
			for _name in exec_names:
				_path = os.path.join(path, _name)
				if os.path.isfile(_path):
					return _path
	return None


class DriveGoogle(Relay):
	"""
	Implements `Relay` for Google Drive with `drive <https://github.com/odeke-em/drive>`_.

	This backend is shiped together with the :mod:`escale.cli.config.googledrive`
	configuration helper.
	"""

	__protocol__ = ['google', 'googledrive']

	_is_multi_path = True

	def __init__(self, client, mount_point, repository, drive_bin=None, config={}, **super_args):
		Relay.__init__(self, client, asstr(mount_point), asstr(repository), **super_args)
		if not mount_point:
			self.logger.info( "default mount point: '%s'", default_mount_point )
			self.mount_point = default_mount_point
		if not drive_bin:
			drive_bin = config.get('drive binary', None)
		drive_bin = drive_binary(drive_bin)
		if not drive_bin:
			raise ValueError("cannot find drive executable file")
		self.drive_bin = drive_bin
		if 'passphrase' in config:
			self.passphrase = "'{}'".format(config['passphrase'])
		else:
			self.passphrase = None

	@property
	def push_extra_arguments(self):
		if self.passphrase:
			return ('-encryption-password', self.passphrase)
		else:
			return ()

	@property
	def pull_extra_arguments(self):
		if self.passphrase:
			return ('-decryption-password', self.passphrase)
		else:
			return ()

	@property
	def mount_point(self):
		return self.address

	@mount_point.setter
	def mount_point(self, p):
		self.address = p

	def open(self):
		self.mount_point = self.ui_controller.mount(self.__protocol__, self.drive_bin, self.mount_point)
		#os.chdir(self.mount_point)

	def close(self, enforce=False):
		if enforce:
			self.ui_controller.umount(self.__protocol__, self.drive_bin, self.mount_point)

	def storageSpace(self):
		"""
		.. warning:: reads used and total spaces of the entire cloud space!
		"""
		# TODO: use `du` on repository instead of `quota`
		output = with_subprocess(self.drive_bin, 'quota', self.mount_point, error=IOError)
		used = None
		total = None
		_used_label = 'Bytes Used:'
		_total_label = 'Total Bytes:'
		for line in output.splitlines():
			if line.startswith(_used_label):
				used = int(line[len(_used_label)+1:].split()[0])
				if total is not None:
					break
			elif line.startswith(_total_label):
				total = int(line[len(_total_label)+1:].split()[0])
				if used is not None:
					break
		return (used, total)

	def _list(self, remote_dir='', recursive=True, stats=[]):
		"""
		"""
		if remote_dir:
			relay_dir = os.path.join(self.repository, asstr(remote_dir))
		else:
			relay_dir = self.repository
		args = []
		if recursive:
			args.append('-recursive')
		if stats:
			args.append('-long')
		args.append(relay_dir)
		kwargs = {'cwd': self.mount_point, 'error': IOError}
		ls = with_subprocess(self.drive_bin,
				'list', '-no-prompt', '-hidden', '-files',
				*args, **kwargs)
		repository = '/'+self.repository
		if stats:
			files = []
			sizes = []
			mtimes = []
			for line in ls.splitlines():
				record = line.split(None, 4)
				size = record[2]
				record = record[-1].split(None, 4)
				path = record[-1]
				path = os.path.relpath(path, repository)
				mtime = ' '.join(record[:3])
				mtime = time.strptime(mtime, '%Y-%m-%d %H:%M:%S +0000')
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
			return [ os.path.relpath(path, repository) for path in ls.splitlines() ]

	def exists(self, remote_file, dirname=None):
		remote_file = asstr(remote_file)
		if dirname:
			relay_file = os.path.join(self.repository, asstr(dirname), remote_file)
		else:
			relay_file = os.path.join(self.repository, remote_file)
		try:
			with_subprocess(self.drive_bin, 'stat', '-hidden', '-quiet',
					relay_file, cwd=self.mount_point, error=IOError)
		except IOError:
			return False
		else:
			return True

	def _push(self, local_file, remote_file, makedirs=True):
		"""
		`makedirs` is ignored (always True).
		"""
		relay_file = os.path.join(self.repository, asstr(remote_file))
		with open(local_file, 'rb') as fd:
			fd.seek(0, os.SEEK_END)
			size = fd.tell()
		if size:
			args = self.push_extra_arguments + \
					('-force', '-hidden', '-piped', relay_file)
			kwargs = dict(stdin=open(local_file, 'rb'), output=False,
					cwd=self.mount_point, error=IOError)
			with_subprocess(self.drive_bin, 'push', *args, **kwargs)
			#with_subprocess(self.drive_bin, 'push', '-hidden',
			#		'-force', '-piped', relay_file,
			#		stdin=open(local_file, 'rb'), output=False,
			#		cwd=self.mount_point, error=IOError)
		else:
			# piped `push` would fail because descriptor already at end of file
			self.logger.debug("file '%s' is empty", local_file)
			try:
				self.unlink(remote_file)
			except IOError:
				pass
			with_subprocess(self.drive_bin, 'new', relay_file,
					cwd=self.mount_point, error=IOError)

	def _get(self, remote_file, local_file, makedirs=True):
		relay_file = os.path.join(self.repository, asstr(remote_file))
		if makedirs:
			dirname = os.path.dirname(local_file)
			if not os.path.isdir(dirname):
				os.makedirs(dirname)
		args = self.pull_extra_arguments + \
				('-quiet', '-hidden', '-desktop-links=false', relay_file)
		kwargs = dict(cwd=self.mount_point, error=IOError)
		try:
			with_subprocess(self.drive_bin, 'pull', *args, **kwargs)
		except IOError as e:
			# drive:
			# "These 1 file(s) would be overwritten. Use -ignore-conflict to override this behaviour"
			# to deal with this issue, we can delete the drivedb file
			self.logger.debug(e.args[0])
			self.logger.warning("drive might have detected a conflict; deleting the 'drivedb' file")
			os.unlink(os.path.join(self.mount_point, '.gd', 'drivedb'))
			with_subprocess(self.drive_bin, 'pull', *args, **kwargs)
		#with_subprocess(self.drive_bin, 'pull', '-hidden', '-quiet',
		#		'-desktop-links=false', relay_file,
		#		cwd=self.mount_point, error=IOError)
		relay_file = join(self.mount_point, relay_file)
		copyfile(relay_file, local_file)
		os.unlink(relay_file)

	def unlink(self, remote_file):
		relay_file = os.path.join(self.repository, asstr(remote_file))
		with_subprocess(self.drive_bin, 'delete', '-hidden', '-quiet', relay_file,
				cwd=self.mount_point, error=IOError)
		#relay_file = os.path.join(self.mount_point, relay_file)
		#if os.path.isfile(relay_file):
		#	os.unlink(relay_file)
		#else:
		#	self.logger.info("missing file '%s'", relay_file)

	def purge(self, remote_dir=''):
		self.unlink(remote_dir)

