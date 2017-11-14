# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#      Contributor: François Laurent

# Copyright © 2017, François Laurent
#      Contribution: ChecksumCache, checksum_cache_prefix

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

from escale.base.essential import PYTHON_VERSION, asstr
from .config import *
from collections import defaultdict

if PYTHON_VERSION == 2:
	#import gdbm as dbm
	import anydbm as dbm
	def asbinary(s):
		if isinstance(s, unicode):
			return s.encode('utf-8')
		else:
			return s
else:
	#import dbm.gnu as dbm
	import dbm
	def asbinary(s):
		if isinstance(s, str):
			return s.encode('utf-8')
		else:
			return s


checksum_cache_prefix = 'cc'


class ChecksumCache(dict):

	__separator__ = ';'

	def __init__(self, cache):
		cache = os.path.expanduser(cache)
		dirname = os.path.dirname(cache)
		if not os.path.isdir(dirname):
			os.makedirs(dirname)
		self.cache = cache

	def __setitem__(self, key, value):
		timestamp, checksum = value
		db = dbm.open(self.cache, 'c')
		try:
			db[key] = '{}{}{}'.format(timestamp, self.__separator__, checksum)
		finally:
			db.close()
	
	def __getitem__(self, key):
		db = dbm.open(self.cache, 'c')
		try:
			value = asstr(db[key])
		finally:
			db.close()
		timestamp, checksum = value.split(self.__separator__)
		return int(timestamp), checksum



def read_checksum_cache(path, log=None):
	"""deprecated
	
	Rename old checksum cache files appending *.old* at the end.
	This function will convert the old cache to the new format."""
	path = os.path.expanduser(path)
	old_cache = path+'.old'
	cache = ChecksumCache(path)
	if os.path.isfile(old_cache) and not os.path.isfile(path):
		state = 0
		try:
			with open(old_cache, 'r') as f:
				for line in f.readlines():
					line = line.rstrip()
					if state == 0:
						resource = line
						state += 1
					elif state == 1:
						mtime = int(line)
						state += 1
					elif state == 2:
						checksum = line
						state = 0
						cache[resource] = (mtime, checksum)
		except IOError as e:
			if log is not None:
				log(e)
			pass
	return cache


def write_checksum_cache(path, cache, log=None):
	"""deprecated"""
	path = os.path.expanduser(path)
	dirname = os.path.dirname(path)
	if not os.path.isdir(dirname):
		os.makedirs(dirname)
	try:
		with open(path, 'w') as f:
			for resource in cache:
				mtime, checksum = cache[resource]
				f.write('{}\n{}\n{}\n'.format(resource, mtime, checksum))
	except IOError as e:
		if log is not None:
			log(e)
		raise


def find_checksum_cache(section, config=None):
	return get_cache_file(config=config, section=section, prefix=checksum_cache_prefix)

