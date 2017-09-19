# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-B license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-B license and that you accept its terms.


from .essential import PROGRAM_NAME
import errno


class MissingSetupFeature(ImportError):
	"""
	This exception helps document missing dependencies at runtime.

	It is designed for setup features that select optional relay and encryption backends.
	"""
	def __str__(self):
		return "install missing dependencies with 'pip install {}[{}]'".format(PROGRAM_NAME, self.args[0])


class QuotaExceeded(EnvironmentError):
	def __init__(self, used_space, quota):
		self.errno = errno.EDQUOT
		self.used_space = used_space
		self.quota = quota
	
	@property
	def args(self):
		return (self.errno, str(self))

	def __repr__(self):
		return "QuotaExceeded({}, {})".format(self.used_space, self.quota)

	def __str__(self):
		return "quota exceeded (used: {} of {}MB)".format(round(self.used_space), round(self.quota))


class LicenseError(ValueError):
	def __init__(self):
		pass

	def __repr__(self):
		return "LicenseError"

	def __str__(self):
		return "License rejected.\nPlease delete all your copies of the software."


ExpressInterrupt = (KeyboardInterrupt, SystemExit)


class PostponeRequest(Exception):
	pass


