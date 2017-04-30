# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

import os
import sys

SYNCACRE_NAME = 'syncacre'

PYTHON_VERSION = sys.version_info[0]


if PYTHON_VERSION == 2:
	binary_type = str
	text_type = unicode
elif PYTHON_VERSION == 3:
	binary_type = bytes
	binary_type = str


def join(dirname, basename):
	'''
	Call :func:`os.path.join` on properly encoded arguments.

	Arguments:

		dirname (str): directory name.

		basename (str): file name.

	Returns:

		str: full path as expected from ``os.path.join(dirname, basename)``.
	'''
	if type(dirname) != type(basename):
		if isinstance(dirname, binary_type):
			dirname = dirname.decode('utf-8')
		else:#if isinstance(basename, binary_type):
			basename = basename.decode('utf-8')
	return os.path.join(dirname, basename)


