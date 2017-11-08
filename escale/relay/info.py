# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent
#   Contribution: Metadata, parse_metadata

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.essential import asstr, basestring
import os.path
# former format
import time
import calendar


class LockInfo(object):

	__slots__ = ['version', 'owner', 'target', 'mode']

	def __init__(self, version=None, owner=None, target=None, mode=None):
		self.owner = None
		if owner:
			self.owner = asstr(owner)
		self.target = target
		self.mode = None
		if mode:
			self.mode = asstr(mode)
		self.version = None
		if version:
			self.version = asstr(version)
		elif self.owner or self.mode:
			self.version = '1.0'

	def __repr__(self):
		if self.version:
			info = ['lock%', self.version]
			if self.owner:
				info += ['\nowner: ', self.owner]
			if self.mode:
				info += ['\nmode: ', self.mode]
			return ''.join(info)
		elif self.owner:
			return self.owner # former format, before LockInfo introduction
		else:
			return ''


def parse_lock_file(file, target=None):
	if target is None:
		target = file
	version = None
	owner = None
	mode = None
	with open(file, 'r') as f:
		line = f.readline()
		if line.startswith('lock%'):
			version = line[5:].rstrip() # 1.0
			for line in f.readlines():
				if line.startswith('owner:'):
					owner = line[6:].strip()
				elif line.startswith('mode:'):
					mode = line[5:].strip()
		else: # first format
			if line:
				owner = line
	return LockInfo(version, owner, target, mode)


former_timestamp_format = '%y%m%d_%H%M%S'


class Metadata(object):

	__slots__ = ['header', 'version', 'target', 'pusher',
			'timestamp', 'timestamp_format', 'checksum',
			'parts', 'pullers',
			'ignored']

	def __init__(self, version=None, target=None, pusher=None, timestamp=None, timestamp_format=None,
			checksum=None, parts=None, pullers=[], **ignored):
		self.header = 'placeholder'
		if pusher:
			pusher = asstr(pusher)
		self.pusher = pusher
		self.target = target
		if timestamp:
			if isinstance(timestamp, basestring):
				if not timestamp_format or timestamp_format is True:
					timestamp_format = former_timestamp_format
				timestamp = time.strptime(timestamp, timestamp_format)
			if isinstance(timestamp, time.struct_time):
				timestamp = calendar.timegm(timestamp)
			timestamp = int(timestamp)
		self.timestamp = timestamp
		self.timestamp_format = timestamp_format
		self.checksum = checksum
		if version:
			version = asstr(version)
		elif pusher or checksum:
			version = '1.0'
		self.version = version
		self.pullers = pullers
		self.ignored = ignored
		if parts:
			parts = int(parts)
		self.parts = parts

	def __repr__(self):
		if self.version:
			if not (self.timestamp or self.checksum):
				raise ValueError("neither 'timestamp' nor 'checksum' are defined")
			info = [self.header, '%', self.version]
			#if self.target:
			#	info += ['\ntarget: ', self.target]
			if self.pusher:
				info += ['\npusher: ', self.pusher]
			if self.timestamp:
				info += ['\ntimestamp: ', str(self.timestamp)]
			if self.checksum:
				info += ['\nchecksum: ', asstr(self.checksum)]
			if self.parts:
				info += ['\nparts: ', str(self.parts)]
			for k in self.ignored:
				info += [ '\n', k, ': ', self.ignored[k] ]
			if self.pullers:
				info.append('\n---pullers---')
				for reader in self.pullers:
					info += ['\n', reader]
			return ''.join(info)
		elif self.timestamp:
			# former format, before :class:`Metadata` introduction
			if not self.timestamp_format or self.timestamp_format is True:
				self.timestamp_format = former_timestamp_format
			timestamp = time.strftime(self.timestamp_format, time.gmtime(self.timestamp))
			if self.pullers:
				return '\n'.join([timestamp]+self.pullers)
			else:
				return timestamp
		else:
			return ''

	@property
	def reader_count(self):
		if not self.pullers:
			return 0
		elif isinstance(self.pullers, (int, float)):
			return self.pullers
		elif isinstance(self.pullers, (list, tuple)):
			return len(self.pullers)

	@property
	def part_count(self):
		return self.parts

	def fileModified(self, local_file=None, checksum=None, hash_function=None, remote=False, debug=None):
		"""
		Tell whether a file has been modified.

		Arguments:

			local_file (str): local file path; file must have a valid last
				modification time.

			checksum (str-like): checksum of file content.

			hash_function (func): hash function that can be applied to the
				content of the `local_file` file if `checksum` is not defined.

			remote (bool): if `True`, `fileModified` tells whether or not
				the remote copy of the file is a modified version of the 
				local file;
				if `False`, `fileModified` tells whether or not the local
				file is a modified version of the remote copy of the file;
				if `None`, `fileModified` tells whether there is any
				difference.

		Returns:

			bool: `True` if file has been modified.

		"""
		file_available = local_file and os.path.isfile(local_file)
		identical = None
		if self.checksum:
			if not checksum and file_available and hash_function is not None:
				with open(local_file, 'rb') as f:
					checksum = hash_function(f.read())
			if checksum:
				identical = checksum == self.checksum
				#if debug and not identical:
				#	debug((local_file, checksum, self.checksum))
				if identical:
					# if files are identical
					return False
		if file_available:
			local_mtime = int(os.path.getmtime(local_file))
			if self.timestamp:
				remote_mtime = self.timestamp
				if identical is False and local_mtime == remote_mtime:
					# likely cause: encryption introduces "salt" in the message
					# checksum should be calculated from plain data
					msg = "is checksum calculated from encrypted data?"
					if debug:
						debug(msg)
					else:
						raise RuntimeError(msg)
				#if debug and local_mtime != remote_mtime:
				#	debug((local_file, local_mtime, remote_mtime))
				if remote is False:
					return remote_mtime < local_mtime
				elif remote is True:
					return local_mtime  < remote_mtime
				elif remote is None:
					return local_mtime != remote_mtime
				else:
					raise ValueError("wrong value for 'remote': '{}'".format(remote))
		else:
			return True
		return None


def parse_metadata(lines, target=None, timestamp_format=None, log=None):
	if isinstance(lines, Metadata):
		return lines
	# read file if not already done
	if not isinstance(lines, (tuple, list)):
		if os.path.isfile(lines):
			with open(lines, 'r') as f:
				lines = f.readlines()
		else:
			lines = lines.splitlines()
	# define a few helpers
	def invalid(line):
		return ValueError("invalid meta attribute: '{}'".format(line))
	convert = {'timestamp': int, 'parts': int}
	# 'parts' can be converted in `Metadata` constructor; 'timestamp' cannot
	# parse
	meta = {}
	if target:
		meta['target'] = target
	pullers = []
	version = None
	if lines:
		line = lines[0].rstrip()
		if line:
			try:
				header, version = line.rsplit('%', 1)
			except ValueError:
				# former format
				meta['timestamp'] = line
				list_pullers = True
			else:
				list_pullers = False
			for line in lines[1:]:
				line = line.rstrip()
				if not line:
					continue
				if list_pullers:
					pullers.append(line)
				elif line[0] in '-=+#%':
					section = line.strip(line[0]).lower()
					if section.startswith('puller') or section.startswith('reader'):
						list_pullers = True
					else:
						# TODO: debug and remove the broken_metadata.txt file creation below
						with open('broken_metadata.txt', 'w') as f:
							for _line in lines:
								f.write(_line+'\n')
						raise invalid(line)
				else:
					try:
						key, value = line.split(':', 2)
					except ValueError:
						raise invalid(line)
					value = value.lstrip()
					try:
						value = convert[key](value)
					except KeyError:
						pass
					meta[key] = value
	# make metadata object
	metadata = Metadata(version=version, pullers=pullers,
			timestamp_format=timestamp_format, **meta)
	# report and purge ignored metadata
	if metadata.ignored:
		if log:
			msg_body = 'unsupported meta attribute'
			if metadata.target:
				for k in metadata.ignored:
					log("{} for resource '{}': '{}'".format(msg_body, metadata.target, k))
			else:
				for k in metadata.ignored:
					log("{}: '{}'".format(msg_body, k))
		metadata.ignored = {}
	return metadata

