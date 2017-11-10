# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#      Contributor: François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.

from .config import *
from collections import defaultdict


def read_checksum_cache(path, log=None):
	state = 0
	cache = {}
	try:
		with open(path, 'r') as f:
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
	with open(path, 'w') as f:
		for resource in cache:
			mtime, checksum = cache[resource]
			f.write('{}\n{}\n{}\n'.format(cache, mtime, checksum))


def find_checksum_cache(section, config=None):
	return get_cache_file(config=config, section=section, prefix='cc')

