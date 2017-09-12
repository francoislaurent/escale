# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


import os
import sys
from escale import PROGRAM_NAME


PYTHON_VERSION = sys.version_info[0]


if PYTHON_VERSION == 2:
	binary_type = str
	text_type = unicode
	basestring = basestring
elif PYTHON_VERSION == 3:
	binary_type = bytes
	text_type = str
	basestring = (bytes, str)


def asbytes(s):
	'''
	Coerce bytes-like object to ``bytes`` (Python 3) or ``str`` (Python 2).
	'''
	if isinstance(s, text_type):
		s = s.encode('utf-8')
	return s

def asstr(s):
	'''
	Coerce string to ``str`` type.

	In Python 2, `s` can be of type ``str`` or ``unicode``.
	In Python 3, `s` can be of type ``bytes`` or ``str``.

	Arguments:

		s (str-like): string.

	Returns:

		str: regular string.

	'''
	if PYTHON_VERSION == 2 and isinstance(s, unicode):
		s = s.encode('utf-8')
	elif PYTHON_VERSION == 3 and isinstance(s, bytes):
		s = s.decode('utf-8')
	return s


def quote_join(words, final=' or ', join=', ', quote="'"):
	"""
	Join words.

	Example:

	>>> quote_join(list(range(1,4)))
	"'1', '2' or '3'"

	Arguments:

		words (list): list of objects that implement `__str__`.

		final (str): connector between the two last words.

		join (str): connector between the first words but the last.

		quote (str or tuple): begin and end quotes for the words.

	Return:

		str: formated sentence.
	"""
	if isinstance(quote, (tuple, list)):
		begin_quote, end_quote = quote
	else:
		begin_quote = end_quote = quote
	slot = '{}{}{}'.format(begin_quote, '{}', end_quote)
	p = [slot]
	for _ in words[1:-1]:
		p.append(join)
		p.append(slot)
	if words[1:]:
		p.append(final)
		p.append(slot)
	return ''.join(p).format(*words)



def join(dirname, *extranames):
	'''
	Combine path elements similarly to :func:`os.path.join`.
	
	Arguments are properly coerced and the extra path elements are
	considered relative even if they begin with a file separator.

	Only slashes (``/``) are considered as valid file separators.

	Arguments:

		dirname (str-like): directory name.

		extraname (str-like): subdirectory or file name.

	Returns:

		str: full path.
	'''
	# remove empty elements
	extranames = [ asstr(s) for s in extranames if s ]
	if extranames:
		# remove beginning slashes
		extranames = [ s[1:] if s[0] in '/' else s for s in extranames ]
		return os.path.join(asstr(dirname), *extranames)
	else:
		return asstr(dirname)


def relpath(path, start):
	'''
	Call os.path.relpath and handle "OSError: [Errno 2] No such file or directory" 
	exceptions on os.getcwd().

	If the `start` directory is not defined, `path` is returned.
	'''
	if not start:
		if path:
			return path
		else:
			return '.'
	while True:
		try:
			return os.path.relpath(path, start)
		except OSError:
			pass


def copyfile(from_file, to_file):
	# from_file is assumed to exist.
	# if to_file is from_file, then it exists.
	# `samefile` raises OSError if to_file does not exist.
	if not (os.path.exists(to_file) and os.path.samefile(from_file, to_file)):
		with open(from_file, 'rb') as i:
			with open(to_file, 'wb') as o:
				o.write(i.read())


class Reporter(object):
	"""
	Base class for log- and user-interface- enabled classes.

	In a feature release, `logger` may become a property.

	Attributes:

		logger (Logger or LoggerAdapter): logger.

		ui_controller (DirectController or UIController): user-interface controller.

	"""

	__slots__ = [ 'logger', 'ui_controller' ]

	def __init__(self, logger=None, ui_controller=None, **ignored):
		self.logger = logger
		if ui_controller is None:
			import escale.cli.controller as ui
			ui_controller = ui.DirectController(logger=logger)
		elif self.logger is None:
			self.logger = ui_controller.logger
		self.ui_controller = ui_controller

