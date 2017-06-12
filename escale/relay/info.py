# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.essential import asstr


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


